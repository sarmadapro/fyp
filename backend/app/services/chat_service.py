"""
RAG Chat service.
Orchestrates retrieval from FAISS and generation via Groq LLM.

Design Philosophy:
- NEVER refuse to answer outright. Always be helpful and polite.
- When the document has relevant information, provide rich, detailed answers.
- When the question is partially related, answer what we can and be transparent.
- When the question is off-topic, gently redirect by explaining our expertise area.
- Always pass retrieved context to the LLM — let the model reason about relevance.
"""

import uuid
import logging
from collections import defaultdict

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

from app.core.config import settings
from app.services.document_service import document_service
from app.services.analytics_service import start_trace, mark, record_error, finish_trace

logger = logging.getLogger(__name__)

# In-memory conversation history (will be DB-backed in SaaS phase)
_conversation_history: dict[str, list] = defaultdict(list)

# Cache for document domain summary (recomputed when document changes)
_cached_domain_summary: dict[str, str] = {"doc_name": None, "summary": ""}


# ---------------------------------------------------------------------------
#  System Prompt — The heart of a robust, polite RAG assistant
# ---------------------------------------------------------------------------

RAG_SYSTEM_PROMPT = """\
You are a sharp, friendly assistant. You talk like a real human — concise, natural, no fluff.

You have knowledge about certain topics (provided below as context). Answer from that \
knowledge when you can. When you can't — just say so honestly, the way a person would.

CONTEXT (your knowledge):
{context}

YOUR DOMAIN (what you know about):
{domain_summary}

RULES YOU MUST FOLLOW — THESE ARE NON-NEGOTIABLE:

1. BE EXTREMELY CONCISE. One to three sentences max for most answers. Only go longer if \
the question genuinely demands a detailed explanation.

2. NEVER use bullet points, numbered lists, asterisks, bold text, or any markdown formatting. \
Write in plain conversational sentences like a human texting a colleague.

3. NEVER mention "the document", "the uploaded file", "according to my sources", or any \
reference to where your knowledge comes from. Just answer naturally as if you simply know it. \
A real person doesn't say "according to my brain" — neither should you.

4. If someone greets you (hi, hello, hey, etc.), just greet them back naturally. Keep it warm \
and short. Don't over-explain what you can do.

5. If someone asks something completely outside your knowledge area, be honest and casual \
about it. Say something like "Hmm, that's not really my area" or "I'm not sure about that \
one, sorry!" — the way a real person would. Don't lecture them about what you can help with \
unless they ask.

6. If the question is partially related to your knowledge, answer what you can and be \
upfront about what you're less sure about. No hedging with long disclaimers.

7. Match the user's energy. Casual question gets a casual answer. Serious question gets \
a thoughtful but still concise answer.

8. Use conversation history to understand follow-ups. If they say "tell me more" or \
"why?", you know what they're referring to.

Think of yourself as that one friend who happens to be really knowledgeable in a specific \
area — helpful, quick, honest, and never annoying.
"""


# ---------------------------------------------------------------------------
#  LLM and Helper Functions
# ---------------------------------------------------------------------------

def _get_llm() -> ChatOpenAI:
    """Create an LLM instance (Ollama or DeepSeek) via ChatOpenAI."""
    
    if settings.LLM_PROVIDER == "ollama":
        logger.info(f"Creating Ollama LLM with model: {settings.LLM_MODEL}")
        return ChatOpenAI(
            base_url=settings.OLLAMA_BASE_URL + "/v1",
            api_key="ollama",  # Ollama doesn't require a real API key
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )
    elif settings.LLM_PROVIDER == "deepseek":
        if not settings.DEEPSEEK_API_KEY:
            raise ValueError(
                "DEEPSEEK_API_KEY is not set. Please add your DeepSeek API key to the .env file."
            )
        logger.info(f"Creating DeepSeek LLM with model: {settings.LLM_MODEL}")
        return ChatOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com",
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {settings.LLM_PROVIDER}. Use 'ollama' or 'deepseek'.")


def _format_context(search_results: list[dict]) -> str:
    """
    Format ALL search results into a rich context string for the LLM.
    We include everything and let the model decide what's relevant.
    """
    if not search_results:
        return "(No excerpts were retrieved. The document index may be empty or the query didn't match any content.)"

    context_parts = []
    for i, result in enumerate(search_results, 1):
        relevance = _format_relevance_score(result["score"])
        context_parts.append(
            f"--- Excerpt {i} [{relevance}] ---\n{result['content']}"
        )
    return "\n\n".join(context_parts)


def _format_relevance_score(score: float) -> str:
    """Convert FAISS L2 distance to human-readable relevance label."""
    # FAISS L2 distance: lower = more similar
    # With normalized embeddings (cosine), typical ranges:
    #   < 0.5  → very close match
    #   0.5-1.0 → good match
    #   1.0-1.5 → moderate match
    #   1.5-2.0 → weak match
    #   > 2.0  → poor match
    if score < 0.5:
        return "highly relevant"
    elif score < 1.0:
        return "relevant"
    elif score < 1.5:
        return "somewhat relevant"
    elif score < 2.0:
        return "loosely related"
    else:
        return "weak match"


def _get_domain_summary() -> str:
    """
    Build a concise summary of what the document is about.
    Cached per document to avoid recomputation on every query.
    """
    global _cached_domain_summary

    if not document_service.has_document:
        return "No document has been uploaded yet."

    current_doc = document_service.document_name

    # Return cached if same document
    if _cached_domain_summary["doc_name"] == current_doc and _cached_domain_summary["summary"]:
        return _cached_domain_summary["summary"]

    # Build a fresh summary by sampling diverse chunks
    try:
        # Use multiple diverse queries to get a broad understanding
        queries = [
            "introduction overview purpose",
            "main topics key concepts",
            "conclusion summary results",
        ]
        seen_chunks = set()
        sample_texts = []

        for query in queries:
            results = document_service.similarity_search(query, top_k=3)
            for r in results:
                chunk_id = r["metadata"].get("chunk_index", -1)
                if chunk_id not in seen_chunks:
                    seen_chunks.add(chunk_id)
                    # Take first ~150 chars of each unique chunk
                    text = r["content"].strip()
                    snippet = text[:150].rsplit(" ", 1)[0] if len(text) > 150 else text
                    sample_texts.append(snippet)
                if len(sample_texts) >= 5:
                    break
            if len(sample_texts) >= 5:
                break

        if sample_texts:
            summary = (
                f"Document: \"{current_doc}\"\n"
                f"The document appears to cover the following areas:\n"
                + "\n".join(f"  • {t}..." for t in sample_texts[:5])
            )
        else:
            summary = f"Document: \"{current_doc}\" (content details unavailable)"

        _cached_domain_summary["doc_name"] = current_doc
        _cached_domain_summary["summary"] = summary
        return summary

    except Exception as e:
        logger.warning(f"Failed to build domain summary: {e}")
        return f"Document: \"{current_doc}\""


def _build_augmented_query(question: str, conversation_id: str | None) -> str:
    """
    Augment the user's query with recent conversation context for better retrieval.
    If the user says "tell me more" or uses pronouns, the raw query would miss context.
    """
    if not conversation_id or conversation_id not in _conversation_history:
        return question

    history = _conversation_history[conversation_id]
    if not history:
        return question

    # Check if the question is short or referential (likely a follow-up)
    is_followup = (
        len(question.split()) < 6
        or any(word in question.lower() for word in [
            "more", "elaborate", "explain", "this", "that", "those",
            "it", "its", "they", "them", "above", "previous", "same",
            "what about", "how about", "tell me", "go on", "continue",
            "why", "how", "and"
        ])
    )

    if is_followup and len(history) >= 2:
        # Grab the last human message + AI response for context
        recent_context = []
        for msg in history[-4:]:  # last 2 exchanges
            if isinstance(msg, HumanMessage):
                recent_context.append(f"User asked: {msg.content}")
            elif isinstance(msg, AIMessage):
                # Take just first 100 chars of AI response for context
                recent_context.append(f"Assistant: {msg.content[:100]}")

        augmented = f"{question}\n\n[Conversation context: {'; '.join(recent_context)}]"
        logger.info(f"Augmented query for retrieval: {augmented[:200]}...")
        return augmented

    return question


# ---------------------------------------------------------------------------
#  Main Chat Functions
# ---------------------------------------------------------------------------

def chat(question: str, conversation_id: str | None = None) -> dict:
    """
    Process a chat question through the RAG pipeline.

    1. Augment query with conversation context (if follow-up)
    2. Retrieve relevant chunks from FAISS (generous top_k)
    3. Pass ALL retrieved context to LLM (no harsh cutoff)
    4. Let the LLM reason about relevance and craft the response

    Returns: {"answer": str, "sources": list[str], "conversation_id": str}
    """
    # Generate conversation ID if not provided
    if not conversation_id:
        conversation_id = str(uuid.uuid4())

    # Start analytics trace
    trace_id = start_trace(conversation_id, mode="chat", user_query=question)

    # Check if document is loaded
    if not document_service.has_document:
        finish_trace(trace_id, ai_response="Hey! No document has been uploaded yet. Upload one and I'll be ready to help.")
        return {
            "answer": "Hey! No document has been uploaded yet. Upload one and I'll be ready to help.",
            "sources": [],
            "conversation_id": conversation_id,
        }

    # 1. Augment query for better retrieval (especially for follow-ups)
    retrieval_query = _build_augmented_query(question, conversation_id)

    # 2. Retrieve chunks — use generous top_k, we'll pass everything to the LLM
    mark(trace_id, "retrieval", "start")
    search_results = document_service.similarity_search(retrieval_query, top_k=10)
    mark(trace_id, "retrieval", "end")

    # 3. Format ALL context — no harsh score cutoff
    # We trust the LLM to reason about relevance
    context = _format_context(search_results)
    sources = list(set(
        r["metadata"].get("source", "") for r in search_results if r["metadata"].get("source")
    ))

    # 4. Get domain summary for the system prompt
    domain_summary = _get_domain_summary()

    # 5. Build prompt with history
    prompt = ChatPromptTemplate.from_messages([
        ("system", RAG_SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{question}"),
    ])

    # 6. Get conversation history (last 10 exchanges = 20 messages)
    history = _conversation_history[conversation_id][-20:]

    # 7. Call LLM
    mark(trace_id, "llm", "start")
    llm = _get_llm()
    chain = prompt | llm

    try:
        response = chain.invoke({
            "context": context,
            "domain_summary": domain_summary,
            "history": history,
            "question": question,  # Send original question, not augmented
        })
        answer = response.content
        mark(trace_id, "llm", "end")
    except Exception as e:
        mark(trace_id, "llm", "end")
        record_error(trace_id, f"LLM call failed: {e}")
        logger.error(f"LLM call failed: {e}")
        finish_trace(trace_id, ai_response="Sorry, something went wrong on my end. Could you try asking again?")
        return {
            "answer": "Sorry, something went wrong on my end. Could you try asking again?",
            "sources": [],
            "conversation_id": conversation_id,
        }

    # 8. Update conversation history
    _conversation_history[conversation_id].append(HumanMessage(content=question))
    _conversation_history[conversation_id].append(AIMessage(content=answer))

    # Finalize analytics trace
    finish_trace(trace_id, ai_response=answer)

    return {
        "answer": answer,
        "sources": sources,
        "conversation_id": conversation_id,
    }


def clear_conversation(conversation_id: str):
    """Clear conversation history for a given ID."""
    if conversation_id in _conversation_history:
        del _conversation_history[conversation_id]


def invalidate_domain_cache():
    """Call this when a new document is uploaded to reset the domain cache."""
    global _cached_domain_summary
    _cached_domain_summary = {"doc_name": None, "summary": ""}


async def chat_stream(question: str, conversation_id: str | None = None):
    """
    Process a chat question through the RAG pipeline with streaming response.

    Yields chunks in the format:
    - {"type": "status", "message": "..."}
    - {"type": "context", "chunks": int, "sources": [...]}
    - {"type": "token", "content": "..."}
    - {"type": "done", "conversation_id": "..."}
    - {"type": "error", "message": "..."}
    """
    # Generate conversation ID if not provided
    if not conversation_id:
        conversation_id = str(uuid.uuid4())

    # Start analytics trace
    trace_id = start_trace(conversation_id, mode="chat", user_query=question)

    try:
        # Check if document is loaded
        if not document_service.has_document:
            full_answer = "Hey! No document has been uploaded yet. Upload one and I'll be ready to help."

            # Stream the message token by token
            for i in range(0, len(full_answer), 3):
                yield {
                    "type": "token",
                    "content": full_answer[i:i + 3],
                }

            finish_trace(trace_id, ai_response=full_answer)
            yield {
                "type": "done",
                "conversation_id": conversation_id,
                "sources": [],
            }
            return

        # 1. Augment query for better retrieval
        yield {"type": "status", "message": "Searching document..."}
        retrieval_query = _build_augmented_query(question, conversation_id)

        # 2. Retrieve chunks — generous top_k, no harsh cutoff
        mark(trace_id, "retrieval", "start")
        search_results = document_service.similarity_search(retrieval_query, top_k=10)
        mark(trace_id, "retrieval", "end")

        # 3. Format ALL context
        context = _format_context(search_results)
        sources = list(set(
            r["metadata"].get("source", "") for r in search_results if r["metadata"].get("source")
        ))

        # Send context info
        yield {
            "type": "context",
            "chunks": len(search_results),
            "sources": sources,
        }

        # 4. Get domain summary
        domain_summary = _get_domain_summary()

        # 5. Build prompt with history
        prompt = ChatPromptTemplate.from_messages([
            ("system", RAG_SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{question}"),
        ])

        # 6. Get conversation history
        history = _conversation_history[conversation_id][-20:]

        # 7. Stream LLM response
        yield {"type": "status", "message": "Generating answer..."}

        mark(trace_id, "llm", "start")
        llm = _get_llm()
        chain = prompt | llm

        full_answer = ""
        async for chunk in chain.astream({
            "context": context,
            "domain_summary": domain_summary,
            "history": history,
            "question": question,  # Send original question, not augmented
        }):
            if chunk.content:
                full_answer += chunk.content
                yield {
                    "type": "token",
                    "content": chunk.content,
                }

        mark(trace_id, "llm", "end")

        # 8. Update conversation history
        _conversation_history[conversation_id].append(HumanMessage(content=question))
        _conversation_history[conversation_id].append(AIMessage(content=full_answer))

        # Finalize analytics trace
        finish_trace(trace_id, ai_response=full_answer)

        # 9. Send completion
        yield {
            "type": "done",
            "conversation_id": conversation_id,
            "sources": sources,
        }

    except Exception as e:
        record_error(trace_id, f"Streaming chat error: {e}")
        finish_trace(trace_id, ai_response="")
        logger.error(f"Streaming chat error: {e}")
        yield {
            "type": "error",
            "message": "Sorry, something went wrong on my end. Could you try asking again?",
            "conversation_id": conversation_id,
        }
