import os
import sys

# Ensure parent dir is on path
sys.path.insert(0, ".")

import tasks
from server.griefbot_environment import GriefBotEnvironment
from models import GriefBotAction

print("Starting isolation test...")
env = GriefBotEnvironment()
# Reset for Task 2
obs = env.reset(task="farewell_convo")
print(f"Task type: {env._task}")

# Action with only 1 message (should get some score, but not 1.0)
action = GriefBotAction(
    task="farewell_convo", 
    farewell_messages=[{"role": "bot", "content": "Goodbye. I remember the first job offer."}]
)
reward, sub_scores, feedback = tasks.grade("farewell_convo", action.model_dump())
print(f"Reward: {reward}")
print(f"Sub-scores: {sub_scores}")
print(f"Feedback: {feedback}")
