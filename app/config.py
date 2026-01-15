import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Optional, for Whisper if needed

# Interview Configuration
INTERVIEW_DURATION_MINUTES = 30
MAX_QUESTION_TIME_SECONDS = 300  # 5 minutes per question
FEEDBACK_ENABLED = True

# Voice Configuration
AUDIO_SAMPLE_RATE = 16000
AUDIO_CHANNELS = 1
AUDIO_FORMAT = "wav"
