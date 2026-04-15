"""
RAG Chat service.
Orchestrates retrieval from FAISS and generation via Groq LLM.
"""

import uuid
import logging
from collections import defaultdict

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

from app.core.config import settings
from app.services.document_service import document_service

logger = logging.getLogger(__name__)

# In-memory conversation history (will be DB-backed in SaaS phase)
_conversation_history: dict[str, list] = defaultdict(list)

# System prompt for the RAG assistant
RAG_SYSTEM_PROMPT = """You are a helpful AI assistant that answers questions based on the provided document context.

**Rules:**
1. Answer ONLY based on the provided context. Do not use external knowledge.
2. If the context does not contain enough information to answer the question, say:
   "I don't have enough information in the uploaded document to answer that question."
3. Be concise but thorough. Use bullet points or numbered lists when appropriate.
4. If quoting from the document, indicate that you are referencing the document.
5. Maintain a professional and friendly tone.

**Context from the document:**
{context}
"""


def _get_llm() -> ChatGroq:
    """Create a Groq LLM instance."""
    return ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
    )


def _format_context(search_results: list[dict]) -> str:
    """Format search results into a context string for the LLM."""
    if not search_results:
        return "No relevant context found in the document."

    context_parts = []
    for i, result in enumerate(search_results, 1):
        context_parts.append(
            f"[Chunk {i}] (relevance score: {result['score']:.3f})\n{result['content']}"
        )
    return "\n\n---\n\n".join(context_parts)


def chat(question: str, conversation_id: str | None = None) -> dict:
    """
    Process a chat question through the RAG pipeline.

    1. Retrieve relevant chunks from FAISS
    2. Format context
    3. Send to Groq LLM with conversation history
    4. Return answer

    Returns: {"answer": str, "sources": list[str], "conversation_id": str}
    """
    # Generate conversation ID if not provided
    if not conversation_id:
        conversation_id = str(uuid.uuid4())

    # Check if document is loaded
    if not document_service.has_document:
        return {
            "answer": "No document has been uploaded yet. Please upload a document first to start chatting.",
            "sources": [],
            "conversation_id": conversation_id,
        }

    # 1. Retrieve relevant chunks
    search_results = document_service.similarity_search(question)

    # 2. Retrieval gate - check if results are relevant enough
    if not search_results or all(r["score"] > 1.5 for r in search_results):
        return {
            "answer": "I don't have enough information in the uploaded document to answer that question. Could you try rephrasing or asking something else about the document?",
            "sources": [],
            "conversation_id": conversation_id,
        }

    # 3. Format context
    context = _format_context(search_results)
    sources = list(set(r["metadata"].get("source", "") for r in search_results))

    # 4. Build prompt with history
    prompt = ChatPromptTemplate.from_messages([
        ("system", RAG_SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{question}"),
    ])

    # 5. Get conversation history (last 10 exchanges)
    history = _conversation_history[conversation_id][-20:]  # 10 pairs of human/ai

    # 6. Call LLM
    llm = _get_llm()
    chain = prompt | llm

    try:
        response = chain.invoke({
            "context": context,
            "history": history,
            "question": question,
        })
        answer = response.content
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return {
            "answer": "I'm sorry, I encountered an error while processing your question. Please try again.",
            "sources": [],
            "conversation_id": conversation_id,
        }

    # 7. Update conversation history
    _conversation_history[conversation_id].append(HumanMessage(content=question))
    _conversation_history[conversation_id].append(AIMessage(content=answer))

    return {
        "answer": answer,
        "sources": sources,
        "conversation_id": conversation_id,
    }


def clear_conversation(conversation_id: str):
    """Clear conversation history for a given ID."""
    if conversation_id in _conversation_history:
        del _conversation_history[conversation_id]
