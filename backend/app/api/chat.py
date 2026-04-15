"""
Chat API routes.
Handles text-based chat with the RAG pipeline.
"""

import logging
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.models.schemas import ChatRequest, ChatResponse
from app.services.chat_service import chat, chat_stream, clear_conversation

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


@router.post("/stream")
async def chat_stream_endpoint(request: ChatRequest):
    """
    Send a question and get a streaming AI-generated answer.
    Returns Server-Sent Events (SSE) for real-time streaming.
    """
    async def event_generator():
        try:
            async for chunk in chat_stream(
                question=request.question,
                conversation_id=request.conversation_id,
            ):
                # Send as Server-Sent Events format
                yield f"data: {json.dumps(chunk)}\n\n"
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering in nginx
        },
    )


@router.delete("/history/{conversation_id}")
async def clear_history(conversation_id: str):
    """Clear conversation history for a given conversation ID."""
    clear_conversation(conversation_id)
    return {"message": "Conversation history cleared."}
