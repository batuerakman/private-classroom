"""
Private Lecture — Streamlit Chat Application

A multi-agent educational system where a Teacher and Student agent
simulate a private lecture on any user-chosen topic. The user observes
and can optionally participate when questions are asked.
"""

import os
import json
import streamlit as st
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from agents.orchestrator import (
    LectureState,
    run_teacher_turn,
    run_student_turn,
    run_teacher_evaluate,
    run_teacher_respond_to_user,
    run_wrap_up,
)
from guardrails.topic_validator import validate_topic
from guardrails.scope_checker import check_scope


# ─── Configuration ─────────────────────────────────────────────────────────────

load_dotenv()

st.set_page_config(
    page_title="Private Lecture",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# ─── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    .stApp {
        font-family: 'Inter', sans-serif;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .topic-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 60vh;
        text-align: center;
    }
    
    .app-title {
        font-size: 2.5rem;
        font-weight: 700;
        color: #000000;
        margin-bottom: 0.5rem;
    }
    
    .app-subtitle {
        font-size: 1.1rem;
        color: #6b7280;
        margin-bottom: 2rem;
        font-weight: 300;
    }
    
    .teacher-msg {
        background: linear-gradient(135deg, #f0f4ff 0%, #e8eeff 100%);
        border-left: 4px solid #667eea;
        padding: 1rem 1.25rem;
        border-radius: 0 12px 12px 0;
        margin: 0.5rem 0;
        font-size: 0.95rem;
        line-height: 1.6;
    }
    
    .student-msg {
        background: linear-gradient(135deg, #fef9f0 0%, #fef3e0 100%);
        border-left: 4px solid #f59e0b;
        padding: 1rem 1.25rem;
        border-radius: 0 12px 12px 0;
        margin: 0.5rem 0;
        font-size: 0.95rem;
        line-height: 1.6;
    }
    
    .user-msg {
        background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
        border-left: 4px solid #22c55e;
        padding: 1rem 1.25rem;
        border-radius: 0 12px 12px 0;
        margin: 0.5rem 0;
        font-size: 0.95rem;
        line-height: 1.6;
    }
    
    .system-msg {
        background: #fef2f2;
        border-left: 4px solid #ef4444;
        padding: 0.75rem 1rem;
        border-radius: 0 12px 12px 0;
        margin: 0.5rem 0;
        font-size: 0.85rem;
        color: #991b1b;
    }
    
    .msg-label {
        font-weight: 600;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.4rem;
    }
    
    .teacher-label { color: #667eea; }
    .student-label { color: #d97706; }
    .user-label { color: #16a34a; }
    
    .question-box {
        background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
        border: 2px solid #667eea;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        text-align: center;
    }
    
    .question-box h4 {
        color: #667eea;
        margin-bottom: 0.5rem;
    }
    
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s;
    }
    
    @keyframes fadeInWord {
        0% { opacity: 0; transform: translateY(2px); }
        100% { opacity: 1; transform: translateY(0); }
    }
    
    .fade-in-word {
        animation: fadeInWord 0.05s ease-out forwards;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)


# ─── Session State ─────────────────────────────────────────────────────────────

if "lecture_started" not in st.session_state:
    st.session_state.lecture_started = False
if "topic" not in st.session_state:
    st.session_state.topic = ""
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "lecture_state" not in st.session_state:
    st.session_state.lecture_state = None
if "phase" not in st.session_state:
    st.session_state.phase = "idle"  # idle, teacher_turn, student_turn, waiting_for_user, done


# ─── Rendering ─────────────────────────────────────────────────────────────────

def render_message(role: str, content: str):
    """Render a chat message with styled bubble."""
    if role == "teacher":
        st.markdown(f"""
        <div class="teacher-msg">
            <div class="msg-label teacher-label">Professor</div>
            {content}
        </div>
        """, unsafe_allow_html=True)
    elif role == "student":
        st.markdown(f"""
        <div class="student-msg">
            <div class="msg-label student-label">Alex (Student)</div>
            {content}
        </div>
        """, unsafe_allow_html=True)
    elif role == "user":
        st.markdown(f"""
        <div class="user-msg">
            <div class="msg-label user-label">You</div>
            {content}
        </div>
        """, unsafe_allow_html=True)
    elif role == "system":
        st.markdown(f"""
        <div class="system-msg">
            ⚠️ {content}
        </div>
        """, unsafe_allow_html=True)


def stream_message(role: str, content: str):
    """Stream a chat message word by word with styled bubble."""
    import time
    placeholder = st.empty()
    
    if role == "teacher":
        prefix = '<div class="teacher-msg"><div class="msg-label teacher-label">Professor</div>'
    elif role == "student":
        prefix = '<div class="student-msg"><div class="msg-label student-label">Alex (Student)</div>'
    elif role == "user":
        prefix = '<div class="user-msg"><div class="msg-label user-label">You</div>'
    elif role == "system":
        prefix = '<div class="system-msg">⚠️ '
        
    suffix = '</div>'
    
    displayed_words = []
    words = content.split(" ")
    for word in words:
        displayed_words.append(word)
        if len(displayed_words) > 1:
            html_content = " ".join(displayed_words[:-1]) + f" <span class='fade-in-word'>{word}</span>"
        else:
            html_content = f"<span class='fade-in-word'>{word}</span>"
            
        placeholder.markdown(prefix + html_content + suffix, unsafe_allow_html=True)
        time.sleep(0.04)



# ─── Topic Input Screen ───────────────────────────────────────────────────────

def show_topic_input():
    st.markdown("""
    <div class="topic-container">
        <div class="app-title">Private Lecture</div>
        <div class="app-subtitle">
            Enter a topic and watch a Teacher and Student bring it to life
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        topic = st.text_input(
            "What would you like to learn about?",
            placeholder="e.g., Bohr's atom model, Stoicism, recursion...",
            label_visibility="collapsed",
            key="topic_input",
        )

        if st.button("Start Lecture →", use_container_width=True, type="primary"):
            if topic:
                validation = validate_topic(topic)
                if validation.is_valid:
                    st.session_state.topic = validation.sanitized_topic
                    st.session_state.lecture_started = True
                    st.session_state.lecture_state = LectureState(validation.sanitized_topic).to_dict()
                    st.session_state.phase = "teacher_turn"
                    st.rerun()
                else:
                    st.error(f"🚫 {validation.rejection_reason}")
            else:
                st.warning("Please enter a topic to begin.")


# ─── Lecture Screen ────────────────────────────────────────────────────────────

def show_lecture():
    # Header
    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 1rem;">
        <div style="font-size: 1.5rem; font-weight: 600; color: #1e293b;">
            Lecture: {st.session_state.topic}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # New Lecture button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col3:
        if st.button("New Lecture", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    st.divider()

    # Render all existing chat messages
    for msg in st.session_state.chat_messages:
        render_message(msg["role"], msg["content"])

    # ── Process the current phase ──
    phase = st.session_state.phase
    state = LectureState.from_dict(st.session_state.lecture_state)

    if phase == "teacher_turn":
        with st.spinner("Professor is speaking..."):
            try:
                display_msgs, state = run_teacher_turn(state)
                st.session_state.lecture_state = state.to_dict()
                st.session_state.chat_messages.extend(display_msgs)

                if state.pending_question:
                    st.session_state.phase = "waiting_for_user"
                elif state.lecture_complete:
                    st.session_state.phase = "done"
                else:
                    st.session_state.phase = "student_turn"
            except Exception as e:
                st.error(f"Error during teacher turn: {str(e)}")
                st.session_state.phase = "idle"
                st.stop()
                
        for msg in display_msgs:
            stream_message(msg["role"], msg["content"])
            
        st.rerun()

    elif phase == "student_turn":
        with st.spinner("Alex is thinking..."):
            try:
                display_msgs, state = run_student_turn(state)
                st.session_state.lecture_state = state.to_dict()
                st.session_state.chat_messages.extend(display_msgs)
                st.session_state.phase = "teacher_turn"
            except Exception as e:
                st.error(f"Error during student turn: {str(e)}")
                st.session_state.phase = "idle"
                st.stop()
                
        for msg in display_msgs:
            stream_message(msg["role"], msg["content"])
            
        st.rerun()

    elif phase == "waiting_for_user":
        # Show the question prompt
        try:
            q_data = json.loads(state.pending_question)
            question_text = q_data.get("question", "The teacher asked a question.")
        except (json.JSONDecodeError, TypeError):
            question_text = "The teacher asked a question."

        st.markdown(f"""
        <div class="question-box">
            <h4>Question for you</h4>
            <p>{question_text}</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("user_answer_form", clear_on_submit=True):
            user_answer = st.text_input(
                "Your answer (or skip to let Alex answer):",
                placeholder="Type your answer...",
                key="user_answer_input",
            )

            col1, col2 = st.columns(2)
            with col1:
                submit_clicked = st.form_submit_button("Submit Answer", use_container_width=True, type="primary")
            with col2:
                skip_clicked = st.form_submit_button("Skip — Let Alex answer", use_container_width=True)

        if submit_clicked:
            if user_answer:
                # Scope check guardrail
                scope_llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite-preview", max_output_tokens=100)
                scope_result = check_scope(user_answer, st.session_state.topic, scope_llm)

                if scope_result.is_on_topic:
                    st.session_state.chat_messages.append({"role": "user", "content": user_answer})
                    st.session_state.phase = "evaluate_user"
                    st.session_state["_pending_answer"] = user_answer
                    st.rerun()
                else:
                    st.warning(
                        f"Let's stay on topic! We're learning about "
                        f"**{st.session_state.topic}**."
                    )
            else:
                st.warning("Please type an answer before submitting.")
                
        elif skip_clicked:
            st.session_state.phase = "student_answers"
            st.rerun()

    elif phase == "student_answers":
        with st.spinner("Alex is answering..."):
            try:
                display_msgs, state = run_student_turn(state, is_answering=True)
                st.session_state.lecture_state = state.to_dict()
                st.session_state.chat_messages.extend(display_msgs)

                # Get the student's answer text for evaluation
                student_answer = ""
                for msg in display_msgs:
                    if msg["role"] == "student":
                        student_answer = msg["content"]
                        break

                st.session_state["_pending_answer"] = student_answer
                st.session_state["_answerer"] = "student (Alex)"
                st.session_state.phase = "evaluate_student"
            except Exception as e:
                st.error(f"Error during student answer: {str(e)}")
                st.session_state.phase = "idle"
                st.stop()
                
        for msg in display_msgs:
            stream_message(msg["role"], msg["content"])
            
        st.rerun()

    elif phase in ("evaluate_user", "evaluate_student"):
        answerer = "user" if phase == "evaluate_user" else "student (Alex)"
        answer_text = st.session_state.get("_pending_answer", "No answer provided")

        with st.spinner("🎓 Professor is evaluating..."):
            try:
                display_msgs, state = run_teacher_evaluate(state, answer_text, answerer)
                st.session_state.lecture_state = state.to_dict()
                st.session_state.chat_messages.extend(display_msgs)

                if state.lecture_complete:
                    # Run wrap-up
                    wrap_msgs, state = run_wrap_up(state)
                    st.session_state.lecture_state = state.to_dict()
                    st.session_state.chat_messages.extend(wrap_msgs)
                    st.session_state.phase = "done"
                else:
                    st.session_state.phase = "teacher_turn"
            except Exception as e:
                st.error(f"Error during evaluation: {str(e)}")
                st.session_state.phase = "idle"
                st.stop()
                
        for msg in display_msgs:
            stream_message(msg["role"], msg["content"])
            
        if state.lecture_complete:
            for msg in wrap_msgs:
                stream_message(msg["role"], msg["content"])
            
        st.rerun()

    elif phase == "respond_to_user":
        user_msg = st.session_state.get("_user_comment", "")
        with st.spinner("🎓 Professor is responding..."):
            try:
                display_msgs, state = run_teacher_respond_to_user(state, user_msg)
                st.session_state.lecture_state = state.to_dict()
                st.session_state.chat_messages.extend(display_msgs)
                st.session_state.phase = "student_turn"
            except Exception as e:
                st.error(f"Error during response: {str(e)}")
                st.session_state.phase = "idle"
                st.stop()
                
        for msg in display_msgs:
            stream_message(msg["role"], msg["content"])
            
        st.rerun()

    elif phase == "done":
        st.divider()
        st.markdown("""
        <div style="text-align: center; padding: 1rem; color: #64748b;">
            🎓 Lecture complete! Click <b>New Lecture</b> to explore a different topic.
        </div>
        """, unsafe_allow_html=True)

    elif phase == "idle":
        # Free-form input for comments mid-lecture
        user_comment = st.chat_input("Add a comment or question...")
        if user_comment:
            scope_llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite-preview", max_output_tokens=100)
            scope_result = check_scope(user_comment, st.session_state.topic, scope_llm)

            if scope_result.is_on_topic:
                st.session_state.chat_messages.append({"role": "user", "content": user_comment})
                st.session_state["_user_comment"] = user_comment
                st.session_state.phase = "respond_to_user"
                st.rerun()
            else:
                st.session_state.chat_messages.append({
                    "role": "system",
                    "content": f"Let's stay on topic! We're learning about "
                              f"<b>{st.session_state.topic}</b>. "
                              f"Start a new lecture to explore something else."
                })
                st.rerun()


# ─── Entry Point ───────────────────────────────────────────────────────────────

def main():
    if not os.getenv("GOOGLE_API_KEY"):
        st.error(
            "⚠️ GOOGLE_API_KEY not found. "
            "Please create a `.env` file with your API key. "
            "See `.env.example` for the template."
        )
        st.stop()

    if not st.session_state.lecture_started:
        show_topic_input()
    else:
        show_lecture()


if __name__ == "__main__":
    main()
