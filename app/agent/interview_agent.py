from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from app.agent.prompts import (
    INTERVIEWER_SYSTEM_PROMPT,
    get_role_specific_prompt,
    FEEDBACK_PROMPT
)
from app.config import GOOGLE_API_KEY
from app.models.schemas import InterviewRole, InterviewStage
from typing import Dict, List, TypedDict, Annotated
import operator

class InterviewState(TypedDict):
    messages: Annotated[List, operator.add]
    session_id: str
    role: InterviewRole
    experience_level: str
    current_stage: InterviewStage
    question_number: int
    questions_asked: List[str]
    answers_given: List[str]
    user_name: str

# Initialize LLM
llm_kwargs = {
    "model": "gemini-2.0-flash-exp",
    "temperature": 0.7,
}
if GOOGLE_API_KEY:
    llm_kwargs["google_api_key"] = GOOGLE_API_KEY

llm = ChatGoogleGenerativeAI(**llm_kwargs)

def get_initial_message(state: InterviewState) -> str:
    """Generate initial greeting based on interview context."""
    role_prompt = get_role_specific_prompt(state["role"].value, state["experience_level"])
    full_prompt = f"{INTERVIEWER_SYSTEM_PROMPT}\n\n{role_prompt}"
    
    name = state.get("user_name", "there")
    greeting = f"""Hello {name}! Welcome to your mock interview. I'm here to help you practice for your {state['experience_level']} level {state['role'].value.replace('_', ' ')} position interview.

I'll be asking you questions and providing feedback along the way. Let's begin!

Are you ready to start? Please introduce yourself briefly."""
    
    return greeting

def interviewer_node(state: InterviewState) -> Dict:
    """Main interviewer node that generates questions and responses."""
    messages = state.get("messages", [])
    
    # Add system prompt if this is the first interaction
    if not messages or len(messages) == 0:
        role_prompt = get_role_specific_prompt(state["role"].value, state["experience_level"])
        system_content = f"{INTERVIEWER_SYSTEM_PROMPT}\n\n{role_prompt}"
        messages = [SystemMessage(content=system_content)]
        
        # Add initial greeting
        initial_greeting = get_initial_message(state)
        messages.append(AIMessage(content=initial_greeting))
    else:
        # Convert dict messages to proper message objects
        formatted_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                if msg.get("type") == "human" or msg.get("role") == "user":
                    formatted_messages.append(HumanMessage(content=msg.get("content", "")))
                elif msg.get("type") == "ai" or msg.get("role") == "assistant":
                    formatted_messages.append(AIMessage(content=msg.get("content", "")))
            else:
                formatted_messages.append(msg)
        messages = formatted_messages
    
    # Get response from LLM
    response = llm.invoke(messages)
    response_content = response.content
    
    # Update state
    new_messages = messages + [response]
    
    return {
        "messages": new_messages,
        "current_stage": determine_stage(state["question_number"]),
        "question_number": state["question_number"] + 1 if "user" in str(messages[-1]).lower() else state["question_number"]
    }

def determine_stage(question_number: int) -> InterviewStage:
    """Determine current interview stage based on question number."""
    if question_number == 0:
        return InterviewStage.INTRODUCTION
    elif question_number <= 3:
        return InterviewStage.TECHNICAL
    elif question_number <= 6:
        return InterviewStage.BEHAVIORAL
    else:
        return InterviewStage.CLOSING

def should_continue(state: InterviewState) -> str:
    """Determine if interview should continue."""
    question_num = state.get("question_number", 0)
    
    if question_num >= 8:  # End after 8 questions
        return "end"
    return "continue"

# Build the graph
graph = StateGraph(InterviewState)

graph.add_node("interviewer", interviewer_node)

graph.set_entry_point("interviewer")

graph.add_conditional_edges(
    "interviewer",
    should_continue,
    {
        "continue": "interviewer",
        "end": END
    }
)

interview_agent = graph.compile()

def generate_feedback(answers: List[str], questions: List[str], role: InterviewRole, experience_level: str) -> Dict:
    """Generate feedback based on interview performance."""
    if not answers or not questions:
        return {
            "overall_score": 0,
            "strengths": [],
            "areas_for_improvement": ["No answers provided"],
            "detailed_feedback": {},
            "recommendations": []
        }
    
    # Create feedback prompt
    interview_summary = "\n\n".join([
        f"Q: {q}\nA: {a}" for q, a in zip(questions, answers)
    ])
    
    feedback_prompt = f"""{FEEDBACK_PROMPT}

Interview Summary:
Role: {role.value.replace('_', ' ')}
Experience Level: {experience_level}

{interview_summary}

Provide detailed feedback in JSON format with:
- overall_score (0-100)
- strengths (list of 2-3 items)
- areas_for_improvement (list of 2-3 items)
- detailed_feedback (object with per-question feedback)
- recommendations (list of actionable items)
"""
    
    response = llm.invoke([HumanMessage(content=feedback_prompt)])
    
    # Parse response (in production, use structured output)
    return {
        "overall_score": 75,  # Placeholder
        "strengths": ["Good communication", "Technical knowledge"],
        "areas_for_improvement": ["Could provide more specific examples"],
        "detailed_feedback": {"summary": response.content},
        "recommendations": ["Practice with more examples", "Focus on STAR method"]
    }
