"""
Tool Permissions — Tool-level guardrail.

Enforces strict allowlists for which agent can call which tools.
This prevents the Student from evaluating answers or the Teacher
from pretending to be confused.
"""

from tools.teacher_tools import create_lesson_plan, pose_question, evaluate_answer
from tools.student_tools import attempt_answer, ask_clarification


# ─── Tool Allowlists ─────────────────────────────────────────────────────────

# Each agent can ONLY access its own tools. This is enforced when
# binding tools to each agent in the orchestrator.

TEACHER_TOOLS = [create_lesson_plan, pose_question, evaluate_answer]
STUDENT_TOOLS = [attempt_answer, ask_clarification]

# Lookup for validation
TEACHER_TOOL_NAMES = {t.name for t in TEACHER_TOOLS}
STUDENT_TOOL_NAMES = {t.name for t in STUDENT_TOOLS}

# All tools combined (for reference only — never bind all tools to one agent)
ALL_TOOLS = TEACHER_TOOLS + STUDENT_TOOLS


def get_tools_for_agent(agent_role: str) -> list:
    """
    Return the list of tools allowed for the given agent role.
    
    Args:
        agent_role: Either "teacher" or "student".
    
    Returns:
        List of LangChain tool objects for that agent.
    
    Raises:
        ValueError: If the agent_role is not recognized.
    """
    if agent_role == "teacher":
        return TEACHER_TOOLS
    elif agent_role == "student":
        return STUDENT_TOOLS
    else:
        raise ValueError(
            f"Unknown agent role '{agent_role}'. Must be 'teacher' or 'student'."
        )


def validate_tool_call(agent_role: str, tool_name: str) -> bool:
    """
    Check whether an agent is allowed to call a specific tool.
    
    This is a runtime check that can be used as an additional safety
    layer beyond the tool binding enforcement.
    
    Args:
        agent_role: Either "teacher" or "student".
        tool_name: Name of the tool being called.
    
    Returns:
        True if the agent is allowed to call this tool, False otherwise.
    """
    if agent_role == "teacher":
        return tool_name in TEACHER_TOOL_NAMES
    elif agent_role == "student":
        return tool_name in STUDENT_TOOL_NAMES
    else:
        return False
