#  MUST be first import
from app.compat.pydantic_py312_patch import *  # noqa

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import Response, StreamingResponse
from app.models.schemas import (
    InterviewRequest,
    InterviewResponse,
    VoiceMessageRequest,
    FeedbackResponse,
    InterviewSession
)
from pydantic import BaseModel
from app.agent.interview_agent import interview_agent, generate_feedback
from app.voice.speech_handler import speech_handler
from app.models.schemas import InterviewStage
from langchain_core.messages import HumanMessage
import uuid
import json
import base64
from typing import Dict
import io
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory session storage
# PRODUCTION NOTE: Replace with Redis, PostgreSQL, or other persistent storage
sessions: Dict[str, Dict] = {}

# Session timeout in seconds (30 minutes)
SESSION_TIMEOUT = 1800


def cleanup_expired_sessions():
    """Remove expired sessions from memory."""
    current_time = datetime.now()
    expired_sessions = []
    
    for session_id, session_data in sessions.items():
        last_activity = session_data.get("last_activity")
        if last_activity:
            time_diff = (current_time - last_activity).total_seconds()
            if time_diff > SESSION_TIMEOUT:
                expired_sessions.append(session_id)
    
    for session_id in expired_sessions:
        del sessions[session_id]
        logger.info(f"Cleaned up expired session: {session_id}")


@router.post("/interview/start", response_model=InterviewSession)
def start_interview(request: InterviewRequest):
    """
    Start a new interview session.
    
    Args:
        request: Interview configuration (role, experience level, name)
        
    Returns:
        New interview session with session_id
    """
    try:
        # Clean up expired sessions periodically
        cleanup_expired_sessions()
        
        session_id = str(uuid.uuid4())
        logger.info(f"Starting new interview session: {session_id}")
        
        initial_state = {
            "messages": [],
            "session_id": session_id,
            "role": request.role,
            "experience_level": request.experience_level,
            "current_stage": InterviewStage.INTRODUCTION,
            "question_number": 0,
            "questions_asked": [],
            "answers_given": [],
            "user_name": request.user_name or "Candidate"
        }
        
        # Use thread_id for LangGraph checkpointing
        config = {"configurable": {"thread_id": session_id}}
        
        # Run initial interview node
        result = interview_agent.invoke(initial_state, config)
        
        # Store session
        sessions[session_id] = {
            "state": result,
            "role": request.role,
            "experience_level": request.experience_level,
            "start_time": datetime.now().isoformat(),
            "last_activity": datetime.now(),
            "config": config
        }
        
        logger.info(f"Interview session {session_id} started successfully")
        
        return {
            "session_id": session_id,
            "role": request.role,
            "experience_level": request.experience_level,
            "questions_asked": [],
            "answers_given": [],
            "current_stage": InterviewStage.INTRODUCTION,
            "start_time": sessions[session_id]["start_time"],
            "end_time": None
        }
        
    except Exception as e:
        logger.error(f"Error starting interview: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to start interview: {str(e)}"
        )


@router.post("/interview/voice", response_model=InterviewResponse)
async def process_voice_message(request: VoiceMessageRequest):
    """
    Process voice input and return voice response.
    
    Args:
        request: Voice message with base64 encoded audio
        
    Returns:
        Interview response with text and audio
    """
    try:
        if request.session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found or expired")
        
        session = sessions[request.session_id]
        session["last_activity"] = datetime.now()  # Update activity timestamp
        state = session["state"]
        config = session["config"]
        
        logger.info(f"Processing voice message for session {request.session_id}")
        
        # Decode and transcribe audio
        try:
            audio_bytes = speech_handler.decode_base64_audio(request.audio_data)
            user_text = speech_handler.speech_to_text(audio_bytes)
        except Exception as e:
            logger.error(f"Audio processing error: {e}")
            raise HTTPException(
                status_code=400, 
                detail=f"Could not process audio: {str(e)}"
            )
        
        if not user_text or user_text.startswith("Error"):
            raise HTTPException(
                status_code=400, 
                detail=f"Could not transcribe audio: {user_text}"
            )
        
        logger.info(f"Transcribed text: {user_text[:100]}...")
        
        # Add user message to state
        user_message = HumanMessage(content=user_text)
        
        # Update state with user message
        updated_state = {
            **state,
            "messages": state.get("messages", []) + [user_message],
            "answers_given": state.get("answers_given", []) + [user_text]
        }
        
        # Get interviewer response using LangGraph
        result = interview_agent.invoke(updated_state, config)
        
        # Extract interviewer's response
        messages = result.get("messages", [])
        last_message = messages[-1] if messages else None
        interviewer_text = (
            last_message.content 
            if hasattr(last_message, 'content') 
            else "Let's continue with the interview."
        )
        
        logger.info(f"Interviewer response: {interviewer_text[:100]}...")
        
        # Generate audio response
        try:
            audio_bytes = speech_handler.text_to_speech(interviewer_text)
            audio_url = (
                f"data:audio/wav;base64,{base64.b64encode(audio_bytes).decode()}" 
                if audio_bytes else None
            )
        except Exception as e:
            logger.warning(f"TTS error: {e}")
            audio_url = None
        
        # Update session with new state
        sessions[request.session_id]["state"] = result
        
        return {
            "text_response": interviewer_text,
            "audio_url": audio_url,
            "session_id": request.session_id,
            "current_stage": result.get("current_stage", InterviewStage.INTRODUCTION),
            "question_number": result.get("question_number", 0),
            "feedback": None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing voice message: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to process voice message: {str(e)}"
        )


class TextMessageRequest(BaseModel):
    """Request model for text-based interview messages."""
    session_id: str
    message: str


@router.post("/interview/text", response_model=InterviewResponse)
def process_text_message(request: TextMessageRequest):
    """
    Process text input (fallback if voice not available).
    
    Args:
        request: Text message request
        
    Returns:
        Interview response with text and optional audio
    """
    try:
        if request.session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found or expired")
        
        session = sessions[request.session_id]
        session["last_activity"] = datetime.now()  # Update activity timestamp
        state = session["state"]
        config = session["config"]
        
        logger.info(f"Processing text message for session {request.session_id}")
        
        # Validate input
        if not request.message or not request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        # Add user message
        user_message = HumanMessage(content=request.message)
        
        updated_state = {
            **state,
            "messages": state.get("messages", []) + [user_message],
            "answers_given": state.get("answers_given", []) + [request.message]
        }
        
        # Get interviewer response using LangGraph
        result = interview_agent.invoke(updated_state, config)
        
        # Extract interviewer's response
        messages = result.get("messages", [])
        last_message = messages[-1] if messages else None
        interviewer_text = (
            last_message.content 
            if hasattr(last_message, 'content') 
            else "Let's continue with the interview."
        )
        
        logger.info(f"Interviewer response: {interviewer_text[:100]}...")
        
        # Generate audio (optional for text mode)
        audio_url = None
        try:
            audio_bytes = speech_handler.text_to_speech(interviewer_text)
            if audio_bytes:
                audio_url = f"data:audio/wav;base64,{base64.b64encode(audio_bytes).decode()}"
        except Exception as e:
            logger.warning(f"TTS error (optional): {e}")
        
        # Update session
        sessions[request.session_id]["state"] = result
        
        return {
            "text_response": interviewer_text,
            "audio_url": audio_url,
            "session_id": request.session_id,
            "current_stage": result.get("current_stage", InterviewStage.INTRODUCTION),
            "question_number": result.get("question_number", 0),
            "feedback": None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing text message: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to process text message: {str(e)}"
        )


@router.get("/interview/{session_id}/feedback", response_model=FeedbackResponse)
def get_interview_feedback(session_id: str):
    """
    Get feedback for completed or ongoing interview.
    
    Args:
        session_id: Interview session ID
        
    Returns:
        Detailed feedback on interview performance
    """
    try:
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = sessions[session_id]
        state = session["state"]
        
        answers = state.get("answers_given", [])
        questions = state.get("questions_asked", [])
        role = session["role"]
        experience_level = session["experience_level"]
        
        logger.info(f"Generating feedback for session {session_id}")
        
        feedback = generate_feedback(answers, questions, role, experience_level)
        
        return feedback
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating feedback: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to generate feedback: {str(e)}"
        )


@router.get("/interview/{session_id}", response_model=InterviewSession)
def get_session(session_id: str):
    """
    Get current session details.
    
    Args:
        session_id: Interview session ID
        
    Returns:
        Current interview session state
    """
    try:
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = sessions[session_id]
        state = session["state"]
        
        return {
            "session_id": session_id,
            "role": session["role"],
            "experience_level": session["experience_level"],
            "questions_asked": state.get("questions_asked", []),
            "answers_given": state.get("answers_given", []),
            "current_stage": state.get("current_stage", InterviewStage.INTRODUCTION),
            "start_time": session.get("start_time", ""),
            "end_time": session.get("end_time")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving session: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to retrieve session: {str(e)}"
        )


@router.post("/interview/{session_id}/end")
def end_interview(session_id: str):
    """
    End an interview session.
    
    Args:
        session_id: Interview session ID
        
    Returns:
        Confirmation message
    """
    try:
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        sessions[session_id]["end_time"] = datetime.now().isoformat()
        logger.info(f"Interview session {session_id} ended")
        
        return {
            "message": "Interview ended successfully",
            "session_id": session_id,
            "end_time": sessions[session_id]["end_time"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ending interview: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to end interview: {str(e)}"
        )


@router.delete("/interview/{session_id}")
def delete_session(session_id: str):
    """
    Delete an interview session from memory.
    
    Args:
        session_id: Interview session ID
        
    Returns:
        Confirmation message
    """
    try:
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        del sessions[session_id]
        logger.info(f"Interview session {session_id} deleted")
        
        return {
            "message": "Session deleted successfully",
            "session_id": session_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to delete session: {str(e)}"
        )


@router.get("/interview/sessions/active")
def get_active_sessions():
    """
    Get list of active sessions (for admin/monitoring).
    
    Returns:
        List of active session IDs and metadata
    """
    try:
        cleanup_expired_sessions()
        
        active_sessions = []
        for session_id, session_data in sessions.items():
            active_sessions.append({
                "session_id": session_id,
                "role": session_data["role"].value,
                "experience_level": session_data["experience_level"],
                "start_time": session_data["start_time"],
                "question_number": session_data["state"].get("question_number", 0),
                "current_stage": session_data["state"].get("current_stage", InterviewStage.INTRODUCTION).value
            })
        
        return {
            "total_active_sessions": len(active_sessions),
            "sessions": active_sessions
        }
        
    except Exception as e:
        logger.error(f"Error retrieving active sessions: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to retrieve active sessions: {str(e)}"
        )
