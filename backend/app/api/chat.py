"""
Chat API endpoints for Marine Intelligence Assistant (MIA)
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.services.chatbot import mia

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessage(BaseModel):
    """Chat message model"""
    role: str = Field(..., description="Role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    message: str = Field(..., description="User message to MIA")
    conversation_history: Optional[List[ChatMessage]] = Field(
        default=None,
        description="Previous conversation history for context"
    )


class ChatResponse(BaseModel):
    """Response model from MIA"""
    response: str = Field(..., description="MIA's response")
    tool_calls: List[Dict[str, Any]] = Field(
        default=[],
        description="Tools/functions called during processing"
    )
    data_confidence: int = Field(
        ...,
        description="Confidence score (0-100) based on data availability"
    )
    sources: List[str] = Field(
        default=[],
        description="Data sources used for the response"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    error: Optional[str] = None


@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """
    Send a message to Marine Intelligence Assistant (MIA)
    
    MIA will analyze the query, call necessary tools to fetch data,
    and provide insights with source citations and confidence scores.
    """
    try:
        # Convert conversation history to OpenAI format
        history = []
        if request.conversation_history:
            for msg in request.conversation_history:
                history.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        # Process message through MIA
        result = await mia.process_message(
            message=request.message,
            conversation_history=history
        )
        
        return ChatResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing message: {str(e)}"
        )


@router.get("/health")
async def chat_health():
    """Check if chat service is available"""
    return {
        "status": "operational",
        "service": "Marine Intelligence Assistant (MIA)",
        "version": "1.0.0",
        "capabilities": [
            "Vessel Intelligence Queries",
            "Pollution Data Analysis",
            "MPA Compliance Monitoring",
            "Platform Guidance",
            "Trend Analysis"
        ]
    }


@router.post("/reset")
async def reset_conversation():
    """Reset conversation context (clears history on client side)"""
    return {
        "status": "success",
        "message": "Conversation context reset. Start a new conversation with MIA."
    }
