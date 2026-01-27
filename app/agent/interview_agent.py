#  MUST be first import
from app.compat.pydantic_py312_patch import *  # noqa


from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from app.agent.prompts import (
    INTERVIEWER_SYSTEM_PROMPT,
    get_role_specific_prompt,
    FEEDBACK_PROMPT
)
from app.config import GOOGLE_API_KEY
from app.models.schemas import InterviewRole, InterviewStage
from typing import Dict, List, TypedDict, Annotated, Optional
import operator
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InterviewState(TypedDict):
    """State schema for the interview agent."""
    messages: Annotated[List[BaseMessage], operator.add]
    session_id: str
    role: InterviewRole
    experience_level: str
    current_stage: InterviewStage
    question_number: int
    questions_asked: List[str]
    answers_given: List[str]
    user_name: str


# -------------------------
# LLM INITIALIZATION
# -------------------------
def initialize_llm():
    """Initialize LLM with proper error handling."""
    if not GOOGLE_API_KEY:
        logger.error("GOOGLE_API_KEY not found in environment variables")
        raise ValueError(
            "GOOGLE_API_KEY is required. Please set it in your .env file."
        )
    
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",  # Updated to latest stable model
            temperature=0.7,
            google_api_key=GOOGLE_API_KEY,
            max_retries=3,  # Add retry logic
            request_timeout=30,  # Add timeout
        )
        logger.info("LLM initialized successfully")
        return llm
    except Exception as e:
        logger.error(f"Failed to initialize LLM: {e}")
        raise


llm = initialize_llm()


# -------------------------
# HELPER FUNCTIONS
# -------------------------
def determine_stage(question_number: int) -> InterviewStage:
    """Determine interview stage based on question number."""
    if question_number == 0:
        return InterviewStage.INTRODUCTION
    elif question_number <= 3:
        return InterviewStage.TECHNICAL
    elif question_number <= 6:
        return InterviewStage.BEHAVIORAL
    else:
        return InterviewStage.CLOSING


def safe_llm_invoke(llm_instance, messages: List[BaseMessage]) -> AIMessage:
    """
    Safely invoke LLM with error handling and fallbacks.
    
    Args:
        llm_instance: The LLM instance to use
        messages: List of messages to send to the LLM
        
    Returns:
        AIMessage with the response
    """
    try:
        response = llm_instance.invoke(messages)

        # Handle empty or invalid responses
        if not response or not getattr(response, "content", None):
            logger.warning("LLM returned empty response, using fallback")
            return AIMessage(
                content="Could you please elaborate on your previous answer?"
            )

        if isinstance(response.content, str) and response.content.strip() == "":
            logger.warning("LLM returned blank content, using fallback")
            return AIMessage(
                content="Thank you for sharing. Let's move to the next question."
            )

        return response

    except Exception as e:
        logger.error(f"LLM invocation error: {e}")
        return AIMessage(
            content="I apologize for the technical difficulty. Let's continue with the interview. Could you tell me more about your background?"
        )


def build_initial_prompt(state: InterviewState) -> str:
    """Build the initial prompt for the interview."""
    role_prompt = get_role_specific_prompt(
        state["role"].value,
        state["experience_level"]
    )

    name = state.get("user_name", "there")

    return f"""
{INTERVIEWER_SYSTEM_PROMPT}

{role_prompt}

You are conducting a mock interview.

Candidate name: {name}
Role: {state['role'].value.replace('_', ' ')}
Experience level: {state['experience_level']}

Start with a warm, professional greeting. Briefly explain the interview structure (introduction, technical questions, behavioral questions, and closing). Then ask the candidate to introduce themselves and tell you about their background.

Keep your response concise and natural.
""".strip()


# -------------------------
# GRAPH NODES
# -------------------------
def interviewer_node(state: InterviewState) -> Dict:
    """
    Main interviewer node that processes user input and generates responses.
    
    Args:
        state: Current interview state
        
    Returns:
        Updated state dict with new messages and metadata
    """
    try:
        messages = list(state.get("messages", []))
        
        # First turn - inject system instructions
        if not messages:
            initial_prompt = build_initial_prompt(state)
            system_message = HumanMessage(content=initial_prompt)
            messages = [system_message]
            
            # Get initial greeting
            response = safe_llm_invoke(llm, messages)
            
            return {
                "messages": [response],
                "current_stage": InterviewStage.INTRODUCTION,
                "question_number": 0,
            }
        
        # Subsequent turns - build conversation context
        # Inject system context for role awareness
        conversation_messages = []
        
        # Add system context at the beginning
        system_context = f"""You are interviewing a {state['experience_level']} level candidate for a {state['role'].value.replace('_', ' ')} position. 
Current stage: {state.get('current_stage', InterviewStage.INTRODUCTION).value}
Questions asked so far: {state.get('question_number', 0)}

Continue the interview naturally. Ask one clear question at a time, provide brief feedback on answers, and guide the conversation through the interview stages."""
        
        conversation_messages.append(HumanMessage(content=system_context))
        
        # Add recent conversation history (last 10 messages to avoid context overflow)
        recent_messages = messages[-10:] if len(messages) > 10 else messages
        conversation_messages.extend(recent_messages)
        
        # Invoke LLM
        response = safe_llm_invoke(llm, conversation_messages)
        
        # Update question counter only when AI asks a new question
        question_number = state.get("question_number", 0)
        if len(messages) > 1 and isinstance(messages[-1], HumanMessage):
            # User just responded, so we're about to ask a new question
            question_number += 1
        
        # Extract question if present
        new_questions = state.get("questions_asked", [])
        if response.content and len(response.content) > 10:
            # Simple heuristic: if response ends with ? it's likely a question
            if "?" in response.content:
                new_questions = new_questions + [response.content]
        
        return {
            "messages": [response],
            "current_stage": determine_stage(question_number),
            "question_number": question_number,
            "questions_asked": new_questions,
        }
        
    except Exception as e:
        logger.error(f"Error in interviewer_node: {e}")
        # Return graceful error message
        return {
            "messages": [AIMessage(content="I apologize for the interruption. Let's continue - could you tell me more about your experience?")],
            "current_stage": state.get("current_stage", InterviewStage.INTRODUCTION),
            "question_number": state.get("question_number", 0),
        }


# -------------------------
# FLOW CONTROL
# -------------------------
def should_continue(state: InterviewState) -> str:
    """Determine if interview should continue or end."""
    question_number = state.get("question_number", 0)
    
    # End after 8 questions (1 intro + 3 technical + 3 behavioral + 1 closing)
    if question_number >= 8:
        logger.info(f"Interview ending at question {question_number}")
        return "end"
    
    return "continue"


# -------------------------
# LANGGRAPH BUILD
# -------------------------
def create_interview_graph():
    """Create and compile the interview graph with checkpointing."""
    graph = StateGraph(InterviewState)
    
    # Add nodes
    graph.add_node("interviewer", interviewer_node)
    
    # Set entry point
    graph.set_entry_point("interviewer")
    
    # Add conditional edges
    graph.add_conditional_edges(
        "interviewer",
        should_continue,
        {
            "continue": "interviewer",
            "end": END,
        },
    )
    
    # Compile with memory saver for state persistence
    memory = MemorySaver()
    compiled_graph = graph.compile(checkpointer=memory)
    
    logger.info("Interview graph compiled successfully")
    return compiled_graph


# Create the compiled graph
interview_agent = create_interview_graph()


# -------------------------
# FEEDBACK GENERATION
# -------------------------
def generate_feedback(
    answers: List[str],
    questions: List[str],
    role: InterviewRole,
    experience_level: str
) -> Dict:
    """
    Generate detailed feedback for the interview.
    
    Args:
        answers: List of candidate answers
        questions: List of questions asked
        role: Interview role
        experience_level: Candidate experience level
        
    Returns:
        Structured feedback dictionary
    """
    if not answers or not questions:
        logger.warning("No answers or questions provided for feedback")
        return {
            "overall_score": 0,
            "strengths": [],
            "areas_for_improvement": ["No answers provided during the interview"],
            "detailed_feedback": {"summary": "Interview was not completed."},
            "recommendations": ["Complete a full interview session to receive feedback"],
        }

    try:
        # Create interview summary
        interview_summary = "\n\n".join(
            f"Q{i+1}: {q}\nA{i+1}: {a}" 
            for i, (q, a) in enumerate(zip(questions, answers))
        )

        feedback_prompt = f"""
{FEEDBACK_PROMPT}

Interview Details:
Role: {role.value.replace('_', ' ')}
Experience Level: {experience_level}
Number of Questions: {len(questions)}

Interview Transcript:
{interview_summary}

Provide detailed, constructive feedback in the following format:

1. Overall Score (0-100): [number]
2. Key Strengths (2-3 points):
   - [strength 1]
   - [strength 2]
   
3. Areas for Improvement (2-3 points):
   - [area 1]
   - [area 2]
   
4. Detailed Analysis:
   [Provide specific analysis of technical knowledge, communication, problem-solving]
   
5. Recommendations (2-3 actionable items):
   - [recommendation 1]
   - [recommendation 2]
""".strip()

        response = safe_llm_invoke(llm, [HumanMessage(content=feedback_prompt)])
        
        # Parse the response (basic parsing, can be improved with structured output)
        feedback_text = response.content
        
        # For now, return structured feedback with parsed content
        # In production, consider using structured output or JSON mode
        return {
            "overall_score": 75,  # Default, parse from response in production
            "strengths": [
                "Clear communication skills demonstrated",
                "Good understanding of fundamental concepts",
            ],
            "areas_for_improvement": [
                "Provide more specific examples from experience",
                "Elaborate on technical problem-solving approaches",
            ],
            "detailed_feedback": {
                "summary": feedback_text,
                "role": role.value,
                "experience_level": experience_level,
                "questions_answered": len(answers),
            },
            "recommendations": [
                "Practice using the STAR method (Situation, Task, Action, Result) for behavioral questions",
                "Review core technical concepts relevant to the role",
                "Prepare specific examples from past projects",
            ],
        }
        
    except Exception as e:
        logger.error(f"Error generating feedback: {e}")
        return {
            "overall_score": 0,
            "strengths": [],
            "areas_for_improvement": ["Unable to generate feedback due to technical error"],
            "detailed_feedback": {"error": str(e)},
            "recommendations": ["Please try again later"],
        }
