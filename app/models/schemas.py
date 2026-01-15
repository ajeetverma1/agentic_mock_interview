from pydantic import BaseModel
from typing import Optional, List, Dict
from enum import Enum

class InterviewRole(str, Enum):
    SOFTWARE_ENGINEER = "software_engineer"
    DATA_SCIENTIST = "data_scientist"
    PRODUCT_MANAGER = "product_manager"
    GENERAL = "general"

class InterviewStage(str, Enum):
    INTRODUCTION = "introduction"
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    CLOSING = "closing"

class InterviewRequest(BaseModel):
    role: InterviewRole = InterviewRole.GENERAL
    experience_level: str = "mid"  # junior, mid, senior
    user_name: Optional[str] = None

class VoiceMessageRequest(BaseModel):
    audio_data: str  # Base64 encoded audio
    session_id: str
    interview_stage: Optional[InterviewStage] = None

class InterviewResponse(BaseModel):
    text_response: str
    audio_url: Optional[str] = None
    session_id: str
    current_stage: InterviewStage
    question_number: int
    feedback: Optional[Dict] = None

class FeedbackResponse(BaseModel):
    overall_score: float
    strengths: List[str]
    areas_for_improvement: List[str]
    detailed_feedback: Dict
    recommendations: List[str]

class InterviewSession(BaseModel):
    session_id: str
    role: InterviewRole
    experience_level: str
    questions_asked: List[str]
    answers_given: List[str]
    current_stage: InterviewStage
    start_time: str
    end_time: Optional[str] = None
