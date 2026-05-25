import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage

load_dotenv()
llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite-preview", max_output_tokens=100)

messages = [
    SystemMessage(content="You are a teacher."),
    HumanMessage(content="Hello"),
    AIMessage(content="", tool_calls=[{"name": "pose_question", "args": {}, "id": "1"}]),
    ToolMessage(content="result", tool_call_id="1"),
    AIMessage(content="Here is a question"),
    HumanMessage(content="My answer is 42"),
]

try:
    response = llm.invoke(messages)
    print("SUCCESS")
except Exception as e:
    print(f"ERROR: {str(e)}")
