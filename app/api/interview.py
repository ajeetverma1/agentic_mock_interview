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
import uuid
import json
import base64
from typing import Dict
import io

router = APIRouter()

# In-memory session storage (use Redis/DB in production)
sessions: Dict[str, Dict] = {}

@router.post("/interview/start", response_model=InterviewSession)
def start_interview(request: InterviewRequest):
    """Start a new interview session."""
    session_id = str(uuid.uuid4())
    
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
    
    # Run initial interview node
    result = interview_agent.invoke(initial_state)
    
    sessions[session_id] = {
        "state": result,
        "role": request.role,
        "experience_level": request.experience_level,
        "start_time": str(uuid.uuid1().time)
    }
    
    # Get the initial greeting
    last_message = result.get("messages", [])[-1] if result.get("messages") else None
    greeting_text = last_message.content if hasattr(last_message, 'content') else str(last_message)
    
    return {
        "session_id": session_id,
        "role": request.role,
        "experience_level": request.experience_level,
        "questions_asked": [],
        "answers_given": [],
        "current_stage": InterviewStage.INTRODUCTION,
        "start_time": str(uuid.uuid1().time),
        "end_time": None
    }

@router.post("/interview/voice", response_model=InterviewResponse)
async def process_voice_message(request: VoiceMessageRequest):
    """Process voice input and return voice response."""
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[request.session_id]
    state = session["state"]
    
    # Decode and transcribe audio
    audio_bytes = speech_handler.decode_base64_audio(request.audio_data)
    user_text = speech_handler.speech_to_text(audio_bytes)
    
    if not user_text or user_text.startswith("Error"):
        raise HTTPException(status_code=400, detail=f"Could not transcribe audio: {user_text}")
    
    # Add user message to state
    current_messages = state.get("messages", [])
    current_messages.append({"role": "user", "content": user_text, "type": "human"})
    
    # Update state with user message
    updated_state = {
        **state,
        "messages": current_messages,
        "answers_given": state.get("answers_given", []) + [user_text]
    }
    
    # Get interviewer response
    result = interview_agent.invoke(updated_state)
    
    # Extract interviewer's response
    last_message = result.get("messages", [])[-1] if result.get("messages") else None
    interviewer_text = last_message.content if hasattr(last_message, 'content') else str(last_message)
    
    # Update session
    sessions[request.session_id]["state"] = result
    
    # Generate audio response
    audio_bytes = speech_handler.text_to_speech(interviewer_text)
    
    # Store question
    questions = state.get("questions_asked", [])
    if interviewer_text and not interviewer_text.startswith("Hello"):
        questions.append(interviewer_text)
    
    updated_state["questions_asked"] = questions
    sessions[request.session_id]["state"] = updated_state
    
    # Return response with audio
    return {
        "text_response": interviewer_text,
        "audio_url": f"data:audio/wav;base64,{base64.b64encode(audio_bytes).decode()}" if audio_bytes else None,
        "session_id": request.session_id,
        "current_stage": result.get("current_stage", InterviewStage.INTRODUCTION),
        "question_number": result.get("question_number", 0),
        "feedback": None
    }

class TextMessageRequest(BaseModel):
    session_id: str
    message: str

@router.post("/interview/text", response_model=InterviewResponse)
def process_text_message(request: TextMessageRequest):
    """Process text input (fallback if voice not available)."""
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[request.session_id]
    state = session["state"]
    
    # Add user message
    current_messages = state.get("messages", [])
    current_messages.append({"role": "user", "content": request.message, "type": "human"})
    
    updated_state = {
        **state,
        "messages": current_messages,
        "answers_given": state.get("answers_given", []) + [request.message]
    }
    
    # Get interviewer response
    result = interview_agent.invoke(updated_state)
    
    last_message = result.get("messages", [])[-1] if result.get("messages") else None
    interviewer_text = last_message.content if hasattr(last_message, 'content') else str(last_message)
    
    # Generate audio
    audio_bytes = speech_handler.text_to_speech(interviewer_text)
    
    # Store question
    questions = state.get("questions_asked", [])
    if interviewer_text and not interviewer_text.startswith("Hello"):
        questions.append(interviewer_text)
    
    updated_state["questions_asked"] = questions
    
    # Update session
    sessions[request.session_id]["state"] = updated_state
    
    return {
        "text_response": interviewer_text,
        "audio_url": f"data:audio/wav;base64,{base64.b64encode(audio_bytes).decode()}" if audio_bytes else None,
        "session_id": request.session_id,
        "current_stage": result.get("current_stage", InterviewStage.INTRODUCTION),
        "question_number": result.get("question_number", 0),
        "feedback": None
    }

@router.get("/interview/{session_id}/feedback", response_model=FeedbackResponse)
def get_interview_feedback(session_id: str):
    """Get feedback for completed interview."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    state = session["state"]
    
    answers = state.get("answers_given", [])
    questions = state.get("questions_asked", [])
    role = session["role"]
    experience_level = session["experience_level"]
    
    feedback = generate_feedback(answers, questions, role, experience_level)
    
    return feedback

@router.get("/interview/{session_id}", response_model=InterviewSession)
def get_session(session_id: str):
    """Get current session details."""
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
        "end_time": None
    }

@router.post("/interview/{session_id}/end")
def end_interview(session_id: str):
    """End an interview session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    sessions[session_id]["state"]["end_time"] = str(uuid.uuid1().time)
    return {"message": "Interview ended", "session_id": session_id}
