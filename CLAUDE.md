# CLAUDE.md — Project Guide for Private Lecture

## What This Project Is
A multi-agent Streamlit chat app for a university course final project. Two AI agents (Teacher + Student) simulate a private lecture on any user-chosen topic. The user observes and can optionally participate when questions are asked.

## Tech Stack
- **Python 3.11+**
- **Streamlit** — Chat UI
- **LangChain + LangGraph** — Agent orchestration, tool binding, structured output
- **Pydantic** — Tool I/O validation, guardrail schemas
- **Google Gemini API** (`langchain-google-genai`) — LLM backbone (free tier)
- **python-dotenv** — API key management

## Project Structure
```
dgd073/
├── app.py                       # Streamlit entry point
├── prompts/
│   ├── teacher.md               # Teacher system prompt
│   └── student.md               # Student system prompt
├── agents/
│   ├── teacher.py               # Teacher agent definition
│   ├── student.py               # Student agent definition
│   └── orchestrator.py          # LangGraph workflow / turn-taking
├── tools/
│   ├── teacher_tools.py         # create_lesson_plan, pose_question, evaluate_answer
│   └── student_tools.py         # attempt_answer, ask_clarification
├── guardrails/
│   ├── topic_validator.py       # Input guardrail — topic validation
│   ├── scope_checker.py         # Output guardrail — on-topic enforcement
│   └── tool_permissions.py      # Tool guardrail — allowlist enforcement
├── models/
│   └── schemas.py               # All Pydantic models
└── tests/
    └── test_guardrails.py
```

## Key Architecture Decisions
- System prompts are stored in `prompts/*.md` files, NOT in Python strings
- All tool inputs/outputs use Pydantic models defined in `models/schemas.py`
- Agent coordination is handled by LangGraph state machine in `agents/orchestrator.py`
- API keys are loaded from `.env` file (never hardcoded)

## Agent Roles
- **Teacher**: Expert persona. Delivers structured lessons, asks Socratic questions, evaluates answers. Has tools: `create_lesson_plan`, `pose_question`, `evaluate_answer`
- **Student**: Learner persona. Asks clarifying questions, attempts answers (often wrong ~40-60% accuracy). Has tools: `attempt_answer`, `ask_clarification`

## Guardrails
1. **Input**: Topic validation — reject harmful/inappropriate/empty topics
2. **Output**: Scope checker — Teacher must stay on the declared topic
3. **Tool**: Strict allowlists — each agent can only call its own tools
4. **Workflow**: Topic lock (can't change topic mid-lecture), max retries per question

## Commands
```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py

# Run tests
pytest tests/
```

## Environment Variables
```
GOOGLE_API_KEY=your-key-here
```

## Important Rules
- Never hardcode API keys
- Always validate tool I/O with Pydantic
- System prompts live in .md files only
- Every agent action must be explainable (for the showcase)
