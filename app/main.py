from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.interview import router as interview_router

app = FastAPI(
    title="Mock Interview Agent API",
    description="AI-powered mock interview agent with voice capabilities",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(interview_router, prefix="/api", tags=["interview"])

@app.get("/")
def root():
    return {
        "message": "Mock Interview Agent API",
        "version": "1.0.0",
        "endpoints": {
            "start_interview": "/api/interview/start",
            "voice_message": "/api/interview/voice",
            "text_message": "/api/interview/text",
            "get_feedback": "/api/interview/{session_id}/feedback",
            "docs": "/docs"
        }
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}
