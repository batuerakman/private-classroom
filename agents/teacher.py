"""
Teacher Agent — Agent definition and invocation logic.

The Teacher agent delivers structured lessons, asks questions,
and evaluates answers. It has access to Teacher-exclusive tools only.
"""

import os
from pathlib import Path
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from guardrails.tool_permissions import get_tools_for_agent


# Load the Teacher system prompt from the .md file
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "teacher.md"


def load_teacher_prompt() -> str:
    """Load the Teacher's system prompt from the markdown file."""
    with open(PROMPT_PATH, "r") as f:
        return f.read()


def create_teacher_agent(model_name: str = "gemini-3.1-flash-lite-preview"):
    """
    Create the Teacher agent with its tools bound.
    
    Args:
        model_name: The Gemini model to use.
    
    Returns:
        A LangChain Runnable (LLM with tools bound).
    """
    llm = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=0.7,
        max_output_tokens=1024,
    )

    # Bind ONLY Teacher tools — enforced by tool_permissions guardrail
    teacher_tools = get_tools_for_agent("teacher")
    agent = llm.bind_tools(teacher_tools)

    return agent


def get_teacher_system_message() -> SystemMessage:
    """Get the Teacher's system message for the conversation."""
    return SystemMessage(content=load_teacher_prompt())
