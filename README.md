# Private Lecture

Two AI agents (Teacher + Student) simulate a private lecture on any topic. Watch, learn, or answer questions yourself.

## Setup

**Requires:** Python 3.11+, [Google Gemini API key](https://aistudio.google.com/apikey) (free)

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your GOOGLE_API_KEY
streamlit run app.py
```

## Stack

Streamlit · LangChain/LangGraph · Pydantic · Google Gemini
