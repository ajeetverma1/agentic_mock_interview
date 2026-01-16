import { useState } from 'react'
import InterviewInterface from './components/InterviewInterface'
import SetupScreen from './components/SetupScreen'
import './App.css'

function App() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [isInterviewStarted, setIsInterviewStarted] = useState(false)

  const handleInterviewStart = (newSessionId: string) => {
    setSessionId(newSessionId)
    setIsInterviewStarted(true)
  }

  const handleInterviewEnd = () => {
    setIsInterviewStarted(false)
    setSessionId(null)
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>🎤 Mock Interview Agent</h1>
        <p>Practice your interview skills with AI-powered voice feedback</p>
      </header>
      
      {!isInterviewStarted ? (
        <SetupScreen onStart={handleInterviewStart} />
      ) : (
        <InterviewInterface 
          sessionId={sessionId!} 
          onEnd={handleInterviewEnd}
        />
      )}
    </div>
  )
}

export default App
