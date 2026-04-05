import sys
sys.path.insert(0, ".")

import tasks
from models import GriefBotAction

print("--- DIAGNOSTICS START ---")
print(f"SCENARIOS available: {'farewell_convo' in tasks.SCENARIOS}")
print(f"grade_farewell_convo available: {hasattr(tasks, 'grade_farewell_convo')}")

# Test Task 2 manually
action_payload = {
    "task": "farewell_convo",
    "farewell_messages": [
        {"role": "bot", "content": "Goodbye Alex. I remember your first job offer. Moving on now."}
    ]
}

print(f"Calling grade with payload: {action_payload}")
try:
    r, s, f = tasks.grade("farewell_convo", action_payload)
    print(f"RESULT SUCCESS!")
    print(f"REWARD: {r}")
    print(f"SUB_SCORES: {s}")
    print(f"FEEDBACK: {f}")
except Exception as e:
    print(f"RESULT ERROR: {e}")
    import traceback
    traceback.print_exc()

print("--- DIAGNOSTICS END ---")
