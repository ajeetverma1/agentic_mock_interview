from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage
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


# -------------------------
# LLM INITIALIZATION (Gemini-safe)
# -------------------------
llm_kwargs = {
    "model": "gemini-2.5-flash",
    "temperature": 0.7,
}


if GOOGLE_API_KEY:
    llm_kwargs["google_api_key"] = GOOGLE_API_KEY

llm = ChatGoogleGenerativeAI(**llm_kwargs)


# -------------------------
# HELPERS
# -------------------------
def determine_stage(question_number: int) -> InterviewStage:
    if question_number == 0:
        return InterviewStage.INTRODUCTION
    elif question_number <= 3:
        return InterviewStage.TECHNICAL
    elif question_number <= 6:
        return InterviewStage.BEHAVIORAL
    else:
        return InterviewStage.CLOSING

def safe_llm_invoke(llm, messages):
    try:
        response = llm.invoke(messages)

        # Gemini sometimes returns empty content
        if not response or not getattr(response, "content", None):
            return AIMessage(
                content="Let's continue. Could you please elaborate on your previous answer?"
            )

        if isinstance(response.content, str) and response.content.strip() == "":
            return AIMessage(
                content="Thanks for sharing. Let's move on to the next question."
            )

        return response

    except Exception:
        return AIMessage(
            content="I encountered a brief issue. Let's continue with the interview."
        )

def normalize_messages(messages: List) -> List:
    """Convert dict-based messages into LangChain message objects."""
    formatted = []

    for msg in messages:
        if isinstance(msg, HumanMessage) or isinstance(msg, AIMessage):
            formatted.append(msg)

        elif isinstance(msg, dict):
            role = msg.get("role") or msg.get("type")
            content = msg.get("content", "")

            if role in ("user", "human"):
                formatted.append(HumanMessage(content=content))
            elif role in ("assistant", "ai"):
                formatted.append(AIMessage(content=content))

    return formatted


def build_initial_prompt(state: InterviewState) -> str:
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

Start with a warm greeting, explain the interview process briefly,
then ask the candidate to introduce themselves.
""".strip()


# -------------------------
# MAIN NODE
# -------------------------
def interviewer_node(state: InterviewState) -> Dict:
    messages = normalize_messages(state.get("messages", []))

    # First turn → inject system instructions as HumanMessage
    if not messages:
        initial_prompt = build_initial_prompt(state)
        messages = [HumanMessage(content=initial_prompt)]

    # Invoke Gemini
    # response = llm.invoke(messages)
    response = safe_llm_invoke(llm, messages)


    # Update counters
    question_number = state.get("question_number", 0)
    if messages and isinstance(messages[-1], HumanMessage):
        question_number += 1

    return {
        "messages": messages + [response],
        "current_stage": determine_stage(question_number),
        "question_number": question_number,
    }

# -------------------------
# FLOW CONTROL
# -------------------------
def should_continue(state: InterviewState) -> str:
    if state.get("question_number", 0) >= 8:
        return "end"
    return "continue"


# -------------------------
# LANGGRAPH BUILD
# -------------------------
graph = StateGraph(InterviewState)

graph.add_node("interviewer", interviewer_node)
graph.set_entry_point("interviewer")

graph.add_conditional_edges(
    "interviewer",
    should_continue,
    {
        "continue": "interviewer",
        "end": END,
    },
)

interview_agent = graph.compile()


# -------------------------
# FEEDBACK GENERATION
# -------------------------
def generate_feedback(
    answers: List[str],
    questions: List[str],
    role: InterviewRole,
    experience_level: str
) -> Dict:

    if not answers or not questions:
        return {
            "overall_score": 0,
            "strengths": [],
            "areas_for_improvement": ["No answers provided"],
            "detailed_feedback": {},
            "recommendations": [],
        }

    interview_summary = "\n\n".join(
        f"Q: {q}\nA: {a}" for q, a in zip(questions, answers)
    )

    feedback_prompt = f"""
{FEEDBACK_PROMPT}

Interview Summary
Role: {role.value.replace('_', ' ')}
Experience Level: {experience_level}

{interview_summary}

Provide structured feedback with:
- overall_score (0–100)
- strengths
- areas_for_improvement
- detailed_feedback
- recommendations
""".strip()

    response = llm.invoke([HumanMessage(content=feedback_prompt)])

    return {
        "overall_score": 75,
        "strengths": ["Clear communication", "Good fundamentals"],
        "areas_for_improvement": ["More concrete examples needed"],
        "detailed_feedback": {"summary": response.content},
        "recommendations": [
            "Practice STAR method",
            "Revise core technical concepts",
        ],
    }
