import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 
  (import.meta.env.DEV ? '/api' : '/api')

export interface InterviewRequest {
  role: 'software_engineer' | 'data_scientist' | 'product_manager' | 'general'
  experience_level: 'junior' | 'mid' | 'senior'
  user_name?: string
}

export interface InterviewResponse {
  text_response: string
  audio_url?: string
  session_id: string
  current_stage: string
  question_number: number
  feedback?: any
}

export interface VoiceMessageRequest {
  audio_data: string
  session_id: string
  interview_stage?: string
}

export interface FeedbackResponse {
  overall_score: number
  strengths: string[]
  areas_for_improvement: string[]
  detailed_feedback: any
  recommendations: string[]
}

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const startInterview = async (request: InterviewRequest) => {
  const response = await api.post('/interview/start', request)
  return response.data
}

export const sendVoiceMessage = async (request: VoiceMessageRequest): Promise<InterviewResponse> => {
  const response = await api.post<InterviewResponse>('/interview/voice', request)
  return response.data
}

export const sendTextMessage = async (sessionId: string, message: string): Promise<InterviewResponse> => {
  const response = await api.post<InterviewResponse>('/interview/text', {
    session_id: sessionId,
    message
  })
  return response.data
}

export const getFeedback = async (sessionId: string): Promise<FeedbackResponse> => {
  const response = await api.get<FeedbackResponse>(`/interview/${sessionId}/feedback`)
  return response.data
}

export const getSession = async (sessionId: string) => {
  const response = await api.get(`/interview/${sessionId}`)
  return response.data
}

export const endInterview = async (sessionId: string) => {
  const response = await api.post(`/interview/${sessionId}/end`)
  return response.data
}
