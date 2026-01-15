import { useState } from 'react'
import { startInterview, InterviewRequest } from '../services/api'
import './SetupScreen.css'

interface SetupScreenProps {
  onStart: (sessionId: string) => void
}

function SetupScreen({ onStart }: SetupScreenProps) {
  const [role, setRole] = useState<'software_engineer' | 'data_scientist' | 'product_manager' | 'general'>('general')
  const [experienceLevel, setExperienceLevel] = useState<'junior' | 'mid' | 'senior'>('mid')
  const [userName, setUserName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleStart = async () => {
    setLoading(true)
    setError('')
    
    try {
      const request: InterviewRequest = {
        role,
        experience_level: experienceLevel,
        user_name: userName || undefined
      }
      
      const session = await startInterview(request)
      onStart(session.session_id)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start interview')
      console.error('Error starting interview:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="setup-screen">
      <div className="setup-card">
        <h2>Interview Setup</h2>
        <p className="setup-description">
          Configure your mock interview session. The AI will ask questions
          appropriate for your role and experience level.
        </p>

        <div className="form-group">
          <label htmlFor="name">Your Name (Optional)</label>
          <input
            id="name"
            type="text"
            value={userName}
            onChange={(e) => setUserName(e.target.value)}
            placeholder="Enter your name"
          />
        </div>

        <div className="form-group">
          <label htmlFor="role">Role</label>
          <select
            id="role"
            value={role}
            onChange={(e) => setRole(e.target.value as any)}
          >
            <option value="general">General Interview</option>
            <option value="software_engineer">Software Engineer</option>
            <option value="data_scientist">Data Scientist</option>
            <option value="product_manager">Product Manager</option>
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="experience">Experience Level</label>
          <select
            id="experience"
            value={experienceLevel}
            onChange={(e) => setExperienceLevel(e.target.value as any)}
          >
            <option value="junior">Junior</option>
            <option value="mid">Mid-Level</option>
            <option value="senior">Senior</option>
          </select>
        </div>

        {error && <div className="error-message">{error}</div>}

        <button
          className="start-button"
          onClick={handleStart}
          disabled={loading}
        >
          {loading ? 'Starting...' : 'Start Interview'}
        </button>

        <div className="setup-info">
          <p>💡 Tips:</p>
          <ul>
            <li>Make sure your microphone is working</li>
            <li>Find a quiet environment</li>
            <li>Speak clearly and take your time</li>
            <li>You can also type your answers if voice isn't available</li>
          </ul>
        </div>
      </div>
    </div>
  )
}

export default SetupScreen
