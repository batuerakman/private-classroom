"""Quick debug script to test the teacher turn end-to-end."""
import os
import logging
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

logging.basicConfig(level=logging.INFO)

from agents.orchestrator import LectureState, run_teacher_turn

# Test run_teacher_turn directly
state = LectureState('Bohr atom model')
display_msgs, state = run_teacher_turn(state)

print("\n=== DISPLAY MESSAGES:", len(display_msgs))
for m in display_msgs:
    print(f"  role={m['role']}, content_len={len(m['content'])}")
    print(f"  preview: {m['content'][:300]}")

print()
print("=== STATE:")
print(f"  lesson_plan: {'SET' if state.lesson_plan_json else 'NONE'}")
print(f"  pending_question: {state.pending_question}")
print(f"  exchanges: {state.exchanges_in_segment}")
print(f"  conversation length: {len(state.conversation)}")

print()
print("=== CONVERSATION DETAIL:")
for i, msg in enumerate(state.conversation):
    t = type(msg).__name__
    content = msg.content or ""
    tc = getattr(msg, 'tool_calls', None)
    print(f"  {i}: {t} content_len={len(content)} tool_calls={[c['name'] for c in tc] if tc else 'none'}")
