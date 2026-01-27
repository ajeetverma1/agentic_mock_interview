import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API Keys
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Optional, for Whisper if needed

# Validate required environment variables
if not GOOGLE_API_KEY:
    logger.error("GOOGLE_API_KEY not found in environment variables")
    logger.error("Please create a .env file with GOOGLE_API_KEY=your_key_here")

# Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")  # development, staging, production
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Interview Configuration
INTERVIEW_DURATION_MINUTES = int(os.getenv("INTERVIEW_DURATION_MINUTES", "30"))
MAX_QUESTION_TIME_SECONDS = int(os.getenv("MAX_QUESTION_TIME_SECONDS", "300"))  # 5 minutes per question
MAX_QUESTIONS = int(os.getenv("MAX_QUESTIONS", "8"))
FEEDBACK_ENABLED = os.getenv("FEEDBACK_ENABLED", "true").lower() == "true"

# Voice Configuration
AUDIO_SAMPLE_RATE = int(os.getenv("AUDIO_SAMPLE_RATE", "16000"))
AUDIO_CHANNELS = int(os.getenv("AUDIO_CHANNELS", "1"))
AUDIO_FORMAT = os.getenv("AUDIO_FORMAT", "wav")

# Session Management
SESSION_TIMEOUT_SECONDS = int(os.getenv("SESSION_TIMEOUT_SECONDS", "1800"))  # 30 minutes
MAX_SESSIONS = int(os.getenv("MAX_SESSIONS", "100"))  # Maximum concurrent sessions

# LLM Configuration
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.0-flash-exp")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "30"))

# CORS Configuration
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"
).split(",")

# Rate Limiting (for production)
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "false").lower() == "true"
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

# Database Configuration (for future use)
DATABASE_URL = os.getenv("DATABASE_URL", None)  # PostgreSQL connection string
REDIS_URL = os.getenv("REDIS_URL", None)  # Redis connection string for session storage

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv(
    "LOG_FORMAT",
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
if ENVIRONMENT == "production" and SECRET_KEY == "your-secret-key-change-in-production":
    logger.warning("Using default SECRET_KEY in production! Please set a secure SECRET_KEY in environment variables.")

# API Configuration
API_V1_PREFIX = "/api"
API_TITLE = "Mock Interview Agent API"
API_VERSION = "1.0.0"
API_DESCRIPTION = "AI-powered mock interview agent with voice capabilities using LangGraph"

# Feature Flags
ENABLE_VOICE = os.getenv("ENABLE_VOICE", "true").lower() == "true"
ENABLE_TEXT = os.getenv("ENABLE_TEXT", "true").lower() == "true"
ENABLE_ANALYTICS = os.getenv("ENABLE_ANALYTICS", "false").lower() == "true"

# Production Settings
if ENVIRONMENT == "production":
    # Override settings for production
    DEBUG = False
    LOG_LEVEL = os.getenv("LOG_LEVEL", "WARNING")
    
    # Ensure critical settings are configured
    if not DATABASE_URL and not REDIS_URL:
        logger.warning(
            "Production mode without DATABASE_URL or REDIS_URL. "
            "Using in-memory storage is not recommended for production."
        )

logger.info(f"Configuration loaded for environment: {ENVIRONMENT}")
logger.info(f"Debug mode: {DEBUG}")
logger.info(f"LLM Model: {LLM_MODEL}")
logger.info(f"Voice enabled: {ENABLE_VOICE}")
logger.info(f"Text enabled: {ENABLE_TEXT}")
