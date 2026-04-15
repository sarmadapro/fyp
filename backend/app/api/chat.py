"""
Chat API routes.
Handles text-based chat with the RAG pipeline.
"""

import logging

from fastapi import APIRouter

from app.models.schemas import ChatRequest, ChatResponse
from app.services.chat_service import chat, clear_conversation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Send a question and get an AI-generated answer based on the uploaded document.
    Optionally pass a conversation_id to maintain context across messages.
    """
    result = chat(
        question=request.question,
        conversation_id=request.conversation_id,
    )
    return ChatResponse(**result)


@router.delete("/history/{conversation_id}")
async def clear_history(conversation_id: str):
    """Clear conversation history for a given conversation ID."""
    clear_conversation(conversation_id)
    return {"message": "Conversation history cleared."}
