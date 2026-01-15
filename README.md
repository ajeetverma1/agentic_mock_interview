# Mock Interview Agent

An AI-powered mock interview application that conducts realistic interviews with voice input/output capabilities. Practice your interview skills with personalized feedback.

## Features

- 🎤 **Voice Input/Output**: Speak your answers and hear the interviewer's questions
- 🤖 **AI-Powered Interviewer**: Powered by Google Gemini AI
- 📝 **Multiple Roles**: Software Engineer, Data Scientist, Product Manager, or General
- 🎯 **Experience Levels**: Junior, Mid-Level, or Senior
- 💬 **Text Fallback**: Type your answers if voice isn't available
- 📊 **Detailed Feedback**: Get comprehensive feedback after the interview
- 🎨 **Modern UI**: Beautiful, responsive React interface

## Project Structure

```
MockInterviewAgent/
├── app/                    # FastAPI backend
│   ├── agent/             # LangGraph interview agent
│   ├── api/               # API routes
│   ├── models/            # Pydantic schemas
│   ├── voice/             # Speech-to-text and text-to-speech
│   └── main.py            # FastAPI app
├── frontend/              # React frontend
│   └── src/
│       ├── components/    # React components
│       └── services/      # API client
└── requirements.txt       # Python dependencies
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- Google API Key for Gemini AI
- Microphone (for voice features)

## Setup

### Backend Setup

1. **Create virtual environment:**
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Linux/Mac:
   source venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   Create a `.env` file in the root directory:
   ```env
   GOOGLE_API_KEY=your_google_api_key_here
   ```

4. **Run the backend:**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start development server:**
   ```bash
   npm run dev
   ```

   The frontend will be available at http://localhost:3000

## Usage

1. **Start the Interview:**
   - Open http://localhost:3000
   - Enter your name (optional)
   - Select your role and experience level
   - Click "Start Interview"

2. **Answer Questions:**
   - Use the voice recorder to speak your answers
   - Or switch to text mode to type your responses
   - The AI will ask follow-up questions based on your answers

3. **Get Feedback:**
   - Click "End Interview" when finished
   - Review your detailed feedback including:
     - Overall score
     - Strengths
     - Areas for improvement
     - Recommendations

## API Endpoints

- `POST /api/interview/start` - Start a new interview session
- `POST /api/interview/voice` - Send voice message and get response
- `POST /api/interview/text` - Send text message and get response
- `GET /api/interview/{session_id}/feedback` - Get interview feedback
- `GET /api/interview/{session_id}` - Get session details
- `POST /api/interview/{session_id}/end` - End interview session

## Technologies Used

### Backend
- **FastAPI**: Web framework
- **LangChain & LangGraph**: Agent orchestration
- **Google Gemini AI**: LLM provider
- **Whisper**: Speech-to-text
- **pyttsx3**: Text-to-speech

### Frontend
- **React 18**: UI library
- **TypeScript**: Type safety
- **Vite**: Build tool
- **react-audio-voice-recorder**: Voice recording
- **Axios**: HTTP client

## Configuration

Edit `app/config.py` to customize:
- Interview duration
- Question time limits
- Audio settings
- Feedback preferences

## Notes

- The first run may take longer as Whisper downloads the model
- Voice features require microphone permissions
- For production, consider using cloud-based TTS/STT services
- Session data is stored in memory (use Redis/DB for production)

## License

MIT License
