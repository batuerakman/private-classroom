"""
Student Agent — Agent definition and invocation logic.

The Student agent listens to lessons, asks clarifying questions,
and attempts answers (often incorrectly). It has access to Student-exclusive tools only.
"""

from pathlib import Path
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage
from guardrails.tool_permissions import get_tools_for_agent


# Load the Student system prompt from the .md file
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "student.md"


def load_student_prompt() -> str:
    """Load the Student's system prompt from the markdown file."""
    with open(PROMPT_PATH, "r") as f:
        return f.read()


def create_student_agent(model_name: str = "gemini-3.1-flash-lite-preview"):
    """
    Create the Student agent with its tools bound.
    
    Args:
        model_name: The Gemini model to use.
    
    Returns:
        A LangChain Runnable (LLM with tools bound).
    """
    llm = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=0.9,  # Higher temperature for more varied/imperfect responses
        max_output_tokens=512,
    )

    # Bind ONLY Student tools — enforced by tool_permissions guardrail
    student_tools = get_tools_for_agent("student")
    agent = llm.bind_tools(student_tools)

    return agent


def get_student_system_message() -> SystemMessage:
    """Get the Student's system message for the conversation."""
    return SystemMessage(content=load_student_prompt())
