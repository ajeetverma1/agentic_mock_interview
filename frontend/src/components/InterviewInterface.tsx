import { useState, useEffect, useRef } from 'react'
import { AudioRecorder, useAudioRecorder } from 'react-audio-voice-recorder'
import { sendVoiceMessage, sendTextMessage, getFeedback, endInterview } from '../services/api'
import './InterviewInterface.css'

interface InterviewInterfaceProps {
  sessionId: string
  onEnd: () => void
}

function InterviewInterface({ sessionId, onEnd }: InterviewInterfaceProps) {
  const [messages, setMessages] = useState<Array<{ type: 'user' | 'interviewer', text: string, audioUrl?: string }>>([])
  const [currentQuestion, setCurrentQuestion] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  const [questionNumber, setQuestionNumber] = useState(0)
  const [showFeedback, setShowFeedback] = useState(false)
  const [feedback, setFeedback] = useState<any>(null)
  const [textInput, setTextInput] = useState('')
  const [useVoice, setUseVoice] = useState(true)
  
  const audioRef = useRef<HTMLAudioElement>(null)
  const recorderControls = useAudioRecorder()

  useEffect(() => {
    // Initial greeting will come from the start endpoint
    // For now, we'll add a welcome message
    setCurrentQuestion('Welcome! Please introduce yourself briefly.')
  }, [])

  const playAudio = (audioUrl: string) => {
    if (audioRef.current) {
      audioRef.current.src = audioUrl
      audioRef.current.play().catch(err => console.error('Error playing audio:', err))
    }
  }

  const handleAudioRecorded = async (audioBlob: Blob) => {
    setIsProcessing(true)
    
    try {
      // Convert blob to base64
      const reader = new FileReader()
      reader.onloadend = async () => {
        const base64Audio = reader.result as string
        
        try {
          const response = await sendVoiceMessage({
            audio_data: base64Audio,
            session_id: sessionId
          })
          
          // Add user message (transcribed)
          setMessages(prev => [...prev, { type: 'user', text: '🎤 [Voice message]' }])
          
          // Add interviewer response
          setMessages(prev => [...prev, {
            type: 'interviewer',
            text: response.text_response,
            audioUrl: response.audio_url
          }])
          
          setCurrentQuestion(response.text_response)
          setQuestionNumber(response.question_number)
          
          // Play audio response if available
          if (response.audio_url) {
            playAudio(response.audio_url)
          }
        } catch (error: any) {
          console.error('Error sending voice message:', error)
          alert('Error processing voice message. Please try typing instead.')
        } finally {
          setIsProcessing(false)
        }
      }
      reader.readAsDataURL(audioBlob)
    } catch (error) {
      console.error('Error processing audio:', error)
      setIsProcessing(false)
    }
  }

  const handleTextSubmit = async () => {
    if (!textInput.trim()) return
    
    setIsProcessing(true)
    const userMessage = textInput
    setTextInput('')
    
    try {
      setMessages(prev => [...prev, { type: 'user', text: userMessage }])
      
      const response = await sendTextMessage(sessionId, userMessage)
      
      setMessages(prev => [...prev, {
        type: 'interviewer',
        text: response.text_response,
        audioUrl: response.audio_url
      }])
      
      setCurrentQuestion(response.text_response)
      setQuestionNumber(response.question_number)
      
      if (response.audio_url) {
        playAudio(response.audio_url)
      }
    } catch (error: any) {
      console.error('Error sending text message:', error)
      alert('Error sending message. Please try again.')
    } finally {
      setIsProcessing(false)
    }
  }

  const handleEndInterview = async () => {
    try {
      await endInterview(sessionId)
      const feedbackData = await getFeedback(sessionId)
      setFeedback(feedbackData)
      setShowFeedback(true)
    } catch (error) {
      console.error('Error ending interview:', error)
      onEnd()
    }
  }

  const handleFinish = () => {
    onEnd()
  }

  return (
    <div className="interview-interface">
      <div className="interview-header">
        <div className="interview-info">
          <span>Question {questionNumber}</span>
          <button className="end-button" onClick={handleEndInterview}>
            End Interview
          </button>
        </div>
      </div>

      {showFeedback && feedback ? (
        <div className="feedback-screen">
          <h2>Interview Feedback</h2>
          <div className="feedback-score">
            <div className="score-circle">
              <span>{Math.round(feedback.overall_score)}</span>
            </div>
            <p>Overall Score</p>
          </div>
          
          <div className="feedback-section">
            <h3>Strengths</h3>
            <ul>
              {feedback.strengths.map((strength: string, idx: number) => (
                <li key={idx}>✓ {strength}</li>
              ))}
            </ul>
          </div>
          
          <div className="feedback-section">
            <h3>Areas for Improvement</h3>
            <ul>
              {feedback.areas_for_improvement.map((area: string, idx: number) => (
                <li key={idx}>→ {area}</li>
              ))}
            </ul>
          </div>
          
          <div className="feedback-section">
            <h3>Recommendations</h3>
            <ul>
              {feedback.recommendations.map((rec: string, idx: number) => (
                <li key={idx}>💡 {rec}</li>
              ))}
            </ul>
          </div>
          
          <button className="finish-button" onClick={handleFinish}>
            Finish
          </button>
        </div>
      ) : (
        <>
          <div className="messages-container">
            {currentQuestion && (
              <div className="current-question">
                <div className="question-bubble">
                  <strong>Interviewer:</strong> {currentQuestion}
                </div>
              </div>
            )}
            
            <div className="messages-list">
              {messages.map((msg, idx) => (
                <div key={idx} className={`message ${msg.type}`}>
                  <div className="message-bubble">
                    {msg.type === 'interviewer' && <strong>Interviewer: </strong>}
                    {msg.type === 'user' && <strong>You: </strong>}
                    {msg.text}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="input-section">
            <div className="input-mode-toggle">
              <button
                className={useVoice ? 'active' : ''}
                onClick={() => setUseVoice(true)}
              >
                🎤 Voice
              </button>
              <button
                className={!useVoice ? 'active' : ''}
                onClick={() => setUseVoice(false)}
              >
                ⌨️ Text
              </button>
            </div>

            {useVoice ? (
              <div className="voice-recorder">
                <AudioRecorder
                  onRecordingComplete={handleAudioRecorded}
                  audioTrackConstraints={{
                    noiseSuppression: true,
                    echoCancellation: true,
                  }}
                  recorderControls={recorderControls}
                />
                {isProcessing && (
                  <div className="processing-indicator">
                    Processing your response...
                  </div>
                )}
              </div>
            ) : (
              <div className="text-input-container">
                <input
                  type="text"
                  value={textInput}
                  onChange={(e) => setTextInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleTextSubmit()}
                  placeholder="Type your answer here..."
                  disabled={isProcessing}
                />
                <button
                  onClick={handleTextSubmit}
                  disabled={isProcessing || !textInput.trim()}
                >
                  Send
                </button>
              </div>
            )}
          </div>

          <audio ref={audioRef} style={{ display: 'none' }} />
        </>
      )}
    </div>
  )
}

export default InterviewInterface
