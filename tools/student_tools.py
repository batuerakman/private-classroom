"""
Student Tools — Tools exclusively available to the Student agent.

These tools let the Student attempt answers and ask clarifying questions.
The Teacher agent CANNOT access these tools (enforced by tool_permissions guardrail).
"""

import json
from langchain_core.tools import tool
from models.schemas import (
    StudentAnswer,
    ClarificationRequest,
    Confidence,
    MisconceptionType,
)


@tool
def attempt_answer(question: str, answer: str, confidence: str, reasoning: str) -> str:
    """
    Attempt to answer a question posed by the Teacher.
    
    The Student uses this tool to formulate and submit an answer. The answer
    should reflect the Student's current understanding — which may be incomplete
    or wrong. The confidence level should roughly match accuracy (don't be 
    highly confident in wrong answers).
    
    Args:
        question: The question being answered.
        answer: The Student's answer text.
        confidence: How confident the Student is — one of "low", "medium", "high".
        reasoning: The Student's reasoning process (may contain errors).
    
    Returns:
        JSON string of the validated StudentAnswer.
    """
    try:
        conf = Confidence(confidence)
    except ValueError:
        return json.dumps({"error": f"Invalid confidence '{confidence}'. Must be one of: low, medium, high."})

    student_answer = StudentAnswer(
        answer=answer,
        confidence=conf,
        reasoning=reasoning,
    )

    return student_answer.model_dump_json()


@tool
def ask_clarification(confused_about: str, what_was_said: str, question: str, misconception_type: str = "none") -> str:
    """
    Ask a clarifying question about something the Teacher explained.
    
    The Student uses this tool when confused about a concept or when they
    want to explore an idea further. The question may stem from a genuine
    misconception (which creates valuable teaching moments).
    
    Args:
        confused_about: What specific concept is confusing.
        what_was_said: What the Teacher said that triggered the confusion.
        question: The clarification question to ask.
        misconception_type: Type of misconception, if any. One of:
            "overgeneralization", "confusion_with_similar", 
            "partial_understanding", "common_myth", "none".
    
    Returns:
        JSON string of the validated ClarificationRequest.
    """
    try:
        misc_type = MisconceptionType(misconception_type)
    except ValueError:
        misc_type = MisconceptionType.NONE

    clarification = ClarificationRequest(
        question=question,
        confused_about=confused_about,
        misconception_type=misc_type,
    )

    return clarification.model_dump_json()
