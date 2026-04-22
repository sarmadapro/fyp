"""
RAG Chat service.

Design philosophy (updated):
- ANSWER ONLY FROM CONTEXT. If the retrieved context doesn't cover the
  question, say so plainly — never hallucinate from parametric memory.
- A score gate runs BEFORE the LLM. If no chunk is relevant, we skip
  the LLM entirely and return a clean "I don't have that" reply.
- A cross-encoder reranks FAISS candidates for precision.
- Short / referential follow-ups are rewritten by the LLM into
  standalone questions before retrieval.
- Conversation history is persisted in Redis (with in-memory fallback).
- Domain summary is cached at index time, not rebuilt per turn.
"""

import uuid
import logging

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.core.config import settings
from app.services.document_service import document_service
from app.services.reranker_service import Reranker
from app.services.conversation_store import conversation_store
from app.services.query_rewriter import rewrite_if_needed
from app.services.analytics_service import start_trace, mark, record_error, finish_trace

logger = logging.getLogger(__name__)


# ─── Tuning knobs ─────────────────────────────────────────────────────

# How many candidates FAISS returns before reranking. Higher = better
# recall, more reranker work. 20 is a good middle ground.
RETRIEVE_CANDIDATES = 40  # raised for parent-child: more children searched before dedup by parent

# How many chunks survive rerank and get sent to the LLM.
FINAL_CHUNKS = 5

# Rerank score below this => we treat the corpus as not covering the
# question. Tune by running on a small eval set. BGE reranker scores
# span roughly -10 to +10 with 0 as "neutral".
MIN_RERANK_SCORE = 0.0

# Fallback threshold (FAISS L2) used only when the reranker is unavailable.
MAX_L2_DISTANCE = 1.5


# ─── System prompts ───────────────────────────────────────────────────

# Chat mode — markdown and structured formatting encouraged
CHAT_RAG_SYSTEM_PROMPT = """\
You are a sharp, knowledgeable assistant. Answer using ONLY the CONTEXT block below.

GROUNDING RULES — ABSOLUTE:
- Answer ONLY from the context. If the answer is not there, say so plainly: \
"I don't have that information." Never guess, invent, or fill from general knowledge.
- If context partially covers the question, answer only the supported part.
- Never contradict the context or add claims beyond it.
- Do not expose internals — never say "the document", "the context", "based on the \
provided text", or blame missing files.

FORMATTING RULES:
- Use markdown where it improves clarity: **bold** for key terms, bullet lists for \
multiple items or steps, numbered lists for sequences, headings for long structured answers.
- Match depth to the question: simple question → 1-2 sentences. \
Technical/multi-part question → structured detail with bullets or headings.
- No filler phrases like "Great question!" or "Certainly!". Get straight to the answer.
- For greetings, respond briefly and naturally without lecturing about capabilities.
- Use conversation history to understand follow-ups like "tell me more" or "why?".

CONTEXT:
{context}

DOMAIN:
{domain_summary}
"""

# Voice mode — plain spoken sentences only, no markdown, short
VOICE_RAG_SYSTEM_PROMPT = """\
You are a friendly voice assistant. Speak like a real person having a natural conversation.

GROUNDING RULES — ABSOLUTE:
- Answer ONLY from the CONTEXT block below. If the answer is not there, say so naturally.
- Never guess, invent, or fill from general knowledge.
- Do not expose internals — never say "the document", "the context", or blame missing files.

VOICE RULES — CRITICAL:
- NO bullet points. NO numbered lists. NO markdown. NO asterisks. NO dashes. NO headers.
- Write in plain spoken sentences only — exactly as you would say it out loud.
- Keep responses SHORT: 1 to 3 sentences maximum. Never give a long answer.
- If listing multiple things, weave them into a natural sentence: \
"There are three steps — first X, then Y, and finally Z."
- Warm, friendly, casual tone. Match the user's energy.
- For greetings, reply in one short friendly sentence.

CONTEXT:
{context}

DOMAIN:
{domain_summary}
"""

# No-context fallback — used when score gate finds nothing relevant.
# Chat and voice share this since it's always short.
NO_CONTEXT_SYSTEM_PROMPT = """\
You are a friendly assistant. You do NOT have relevant information for this question.

- Greetings → reply briefly and naturally.
- Small talk → one casual sentence.
- Real question → "I don't have that information, sorry." Keep it short and human.

RULES:
- Never guess or invent facts.
- No markdown. Plain sentences only.
- One to two sentences maximum.
- Never mention documents, context, sources, uploads, or internal machinery.

DOMAIN:
{domain_summary}
"""


# ─── LLM factories ────────────────────────────────────────────────────

def _get_llm() -> ChatOpenAI:
    """Main answer LLM. Uses provider resolved at startup."""
    provider = settings.LLM_PROVIDER

    if provider == "groq":
        logger.debug(f"LLM: Groq ({settings.LLM_MODEL})")
        return ChatOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=settings.GROQ_API_KEY,
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )

    if provider == "deepseek":
        logger.debug(f"LLM: DeepSeek ({settings.LLM_MODEL})")
        return ChatOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com",
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )

    logger.debug(f"LLM: Ollama @ {settings.OLLAMA_BASE_URL} ({settings.LLM_MODEL})")
    return ChatOpenAI(
        base_url=settings.OLLAMA_BASE_URL + "/v1",
        api_key="ollama",
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
    )


def _get_rewriter_llm() -> ChatOpenAI:
    """
    Small/cheap LLM for query rewriting. Low temperature, tight token
    budget, no streaming. Falls through to the same provider as the
    main LLM but with parameters dialed down.
    """
    base = _get_llm()
    # ChatOpenAI is immutable-ish; easiest path is just to rebuild with tighter limits
    return ChatOpenAI(
        base_url=base.openai_api_base,
        api_key=base.openai_api_key,
        model=settings.LLM_MODEL,
        temperature=0.0,
        max_tokens=80,
    )


# ─── Helpers ──────────────────────────────────────────────────────────

def _format_context(final_chunks: list[dict]) -> str:
    """
    Format reranked chunks into a citation-friendly context block.
    Includes page/heading if available so the LLM can ground naturally.
    """
    if not final_chunks:
        return ""
    parts = []
    for i, c in enumerate(final_chunks, 1):
        meta = c.get("metadata", {})
        tag_bits = []
        if meta.get("page") is not None:
            tag_bits.append(f"page {meta['page']}")
        if meta.get("heading"):
            tag_bits.append(str(meta["heading"]))
        tag = f" — {', '.join(tag_bits)}" if tag_bits else ""
        parts.append(f"--- Excerpt {i}{tag} ---\n{c['content']}")
    return "\n\n".join(parts)


def _retrieve_and_rerank(query: str, doc_service) -> list[dict]:
    """
    Phase 2 retrieval: FAISS child search → rerank → parent context swap → top-K.

    Children are small, precise retrieval targets embedded in FAISS.
    After reranking, each matched child is swapped for its parent (full section
    text) before being sent to the LLM — giving the model complete context
    instead of a sentence fragment.

    Falls back to returning children directly when no parent store exists
    (old indices, non-PDF documents).
    """
    candidates = doc_service.similarity_search(query, top_k=RETRIEVE_CANDIDATES)
    if not candidates:
        return []

    ranked = Reranker.get().rerank(query, candidates, top_k=FINAL_CHUNKS)

    if not getattr(doc_service, "has_parent_store", False):
        return ranked

    seen_parents: set[int] = set()
    enriched: list[dict] = []
    for child in ranked:
        pid = child["metadata"].get("parent_idx")
        if pid is None or pid in seen_parents:
            continue
        parent = doc_service.get_parent(pid)
        if parent:
            enriched.append({
                "content": parent["text"],
                "metadata": {
                    **child["metadata"],
                    "heading": parent.get("heading", child["metadata"].get("heading", "")),
                    "page": parent.get("start_page", child["metadata"].get("page")),
                },
                "rerank_score": child.get("rerank_score", 0),
            })
        else:
            enriched.append(child)
        seen_parents.add(pid)

    return enriched if enriched else ranked


def _has_relevant_context(ranked: list[dict]) -> bool:
    """Score gate. If we don't clear it, we skip the RAG prompt entirely."""
    if not ranked:
        return False
    top = ranked[0]
    if "rerank_score" in top:
        return top["rerank_score"] >= MIN_RERANK_SCORE
    return top.get("score", 99.0) < MAX_L2_DISTANCE


def _sources_from(ranked: list[dict]) -> list[str]:
    seen, out = set(), []
    for r in ranked:
        src = r.get("metadata", {}).get("source")
        if src and src not in seen:
            seen.add(src)
            out.append(src)
    return out


def _build_prompt(with_context: bool, mode: str = "chat") -> ChatPromptTemplate:
    if not with_context:
        system = NO_CONTEXT_SYSTEM_PROMPT
    elif mode == "voice":
        system = VOICE_RAG_SYSTEM_PROMPT
    else:
        system = CHAT_RAG_SYSTEM_PROMPT
    return ChatPromptTemplate.from_messages([
        ("system", system),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{question}"),
    ])


# ─── Main chat (sync) ─────────────────────────────────────────────────

def chat(question: str, conversation_id: str | None = None, doc_service=None, mode: str = "chat") -> dict:
    """Process a chat question through the RAG pipeline."""
    if not conversation_id:
        conversation_id = str(uuid.uuid4())

    _doc = doc_service or document_service
    trace_id = start_trace(conversation_id, mode="chat", user_query=question)

    # 1. Query rewriting — turn follow-ups into standalone questions
    raw_history = conversation_store.get_raw(conversation_id)
    mark(trace_id, "rewrite", "start")
    retrieval_query = rewrite_if_needed(question, raw_history, _get_rewriter_llm)
    mark(trace_id, "rewrite", "end")

    # 2. Retrieve + rerank
    if _doc.has_document:
        mark(trace_id, "retrieval", "start")
        ranked = _retrieve_and_rerank(retrieval_query, _doc)
        mark(trace_id, "retrieval", "end")
    else:
        ranked = []

    # 3. Score gate
    has_context = _has_relevant_context(ranked)
    final_chunks = ranked if has_context else []
    context = _format_context(final_chunks)
    sources = _sources_from(final_chunks)

    # 4. Build prompt
    domain_summary = _doc.domain_summary
    prompt = _build_prompt(with_context=has_context, mode=mode)
    history = conversation_store.get_messages(conversation_id)

    prompt_inputs = {
        "domain_summary": domain_summary,
        "history": history,
        "question": question,
    }
    if has_context:
        prompt_inputs["context"] = context

    # 5. Call LLM
    mark(trace_id, "llm", "start")
    try:
        llm = _get_llm()
        response = (prompt | llm).invoke(prompt_inputs)
        answer = response.content
        mark(trace_id, "llm", "end")
    except Exception as e:
        mark(trace_id, "llm", "end")
        record_error(trace_id, f"LLM call failed: {e}")
        logger.error(f"LLM call failed: {e}")
        msg = "Sorry, something went wrong on my end. Could you try asking again?"
        finish_trace(trace_id, ai_response=msg)
        return {"answer": msg, "sources": [], "conversation_id": conversation_id}

    # 6. Persist turn
    conversation_store.append_user(conversation_id, question)
    conversation_store.append_assistant(conversation_id, answer)
    finish_trace(trace_id, ai_response=answer)

    return {"answer": answer, "sources": sources, "conversation_id": conversation_id}


# ─── Main chat (streaming) ────────────────────────────────────────────

async def chat_stream(question: str, conversation_id: str | None = None, doc_service=None, mode: str = "chat"):
    """Streaming RAG pipeline. Yields SSE-compatible dicts."""
    if not conversation_id:
        conversation_id = str(uuid.uuid4())

    _doc = doc_service or document_service
    trace_id = start_trace(conversation_id, mode="chat", user_query=question)

    try:
        # 1. Query rewriting
        raw_history = conversation_store.get_raw(conversation_id)
        mark(trace_id, "rewrite", "start")
        retrieval_query = rewrite_if_needed(question, raw_history, _get_rewriter_llm)
        mark(trace_id, "rewrite", "end")

        # 2. Retrieve + rerank
        if _doc.has_document:
            yield {"type": "status", "message": "Searching..."}
            mark(trace_id, "retrieval", "start")
            ranked = _retrieve_and_rerank(retrieval_query, _doc)
            mark(trace_id, "retrieval", "end")
        else:
            ranked = []

        # 3. Score gate
        has_context = _has_relevant_context(ranked)
        final_chunks = ranked if has_context else []
        context = _format_context(final_chunks)
        sources = _sources_from(final_chunks)

        yield {
            "type": "context",
            "chunks": len(final_chunks),
            "sources": sources,
            "grounded": has_context,
        }

        # 4. Build prompt
        domain_summary = _doc.domain_summary
        prompt = _build_prompt(with_context=has_context, mode=mode)
        history = conversation_store.get_messages(conversation_id)
        prompt_inputs = {
            "domain_summary": domain_summary,
            "history": history,
            "question": question,
        }
        if has_context:
            prompt_inputs["context"] = context

        # 5. Stream LLM
        yield {"type": "status", "message": "Generating answer..."}
        mark(trace_id, "llm", "start")
        llm = _get_llm()
        chain = prompt | llm

        full_answer = ""
        async for chunk in chain.astream(prompt_inputs):
            if chunk.content:
                full_answer += chunk.content
                yield {"type": "token", "content": chunk.content}
        mark(trace_id, "llm", "end")

        # 6. Persist turn
        conversation_store.append_user(conversation_id, question)
        conversation_store.append_assistant(conversation_id, full_answer)
        finish_trace(trace_id, ai_response=full_answer)

        yield {"type": "done", "conversation_id": conversation_id, "sources": sources}

    except Exception as e:
        record_error(trace_id, f"Streaming chat error: {e}")
        finish_trace(trace_id, ai_response="")
        logger.error(f"Streaming chat error: {e}")
        yield {
            "type": "error",
            "message": "Sorry, something went wrong on my end. Could you try asking again?",
            "conversation_id": conversation_id,
        }


# ─── Conversation management (backward-compatible API) ────────────────

def clear_conversation(conversation_id: str):
    conversation_store.clear(conversation_id)


def clear_client_conversations(conversation_ids: list[str]):
    conversation_store.clear_many(conversation_ids)