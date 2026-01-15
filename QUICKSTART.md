# Quick Start Guide

## Project Location
```
c:\Users\ajeet\vscode_code_folder\GEMINI\MockInterviewAgent
```

## Step-by-Step Setup

### 1. Backend Setup

Open a terminal and run:

```powershell
# Navigate to project
cd c:\Users\ajeet\vscode_code_folder\GEMINI\MockInterviewAgent

# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows PowerShell)
venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Create .env file with your Google API key
# Copy the content below to a new file named .env
```

Create a `.env` file in the project root:
```env
GOOGLE_API_KEY=your_google_api_key_here
```

Then start the backend:
```powershell
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup

Open a NEW terminal window and run:

```powershell
# Navigate to frontend directory
cd c:\Users\ajeet\vscode_code_folder\GEMINI\MockInterviewAgent\frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### 3. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## Troubleshooting

### If Python packages fail to install:
- Make sure you're using Python 3.11+
- Try: `pip install --upgrade pip` first

### If npm install fails:
- Make sure Node.js 18+ is installed
- Try: `npm install --legacy-peer-deps`

### If Whisper model download is slow:
- First run will download ~150MB model
- This is normal and only happens once

### If microphone doesn't work:
- Check browser permissions
- Use text mode as fallback

## Running Both Services

You need TWO terminal windows:

**Terminal 1 (Backend):**
```powershell
cd c:\Users\ajeet\vscode_code_folder\GEMINI\MockInterviewAgent
venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 (Frontend):**
```powershell
cd c:\Users\ajeet\vscode_code_folder\GEMINI\MockInterviewAgent\frontend
npm run dev
```

Then open http://localhost:3000 in your browser!
