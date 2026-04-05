try:
    import os
    import sys
    import traceback
    
    # Force PYTHONPATH
    sys.path.insert(0, ".")
    
    import tasks
    import models
    from server.griefbot_environment import GriefBotEnvironment

    print(f"PYTHONPATH: {os.environ.get('PYTHONPATH')}")
    print(f"tasks.py path: {tasks.__file__}")
    print(f"models.py path: {models.__file__}")
    print(f"GriefBotEnvironment class: {GriefBotEnvironment}")

    env = GriefBotEnvironment()
    obs = env.reset(task="farewell_convo")
    print(f"Reset OBS feedback: {obs.feedback}")
    print(f"Reset OBS task: {obs.task}")

    from models import GriefBotAction
    # Test Task 2
    action = GriefBotAction(
        task="farewell_convo", 
        farewell_messages=[{"role": "bot", "content": "Goodbye Leo. Remember your first job offer?"}]
    )
    obs2 = env.step(action)
    print(f"Step reward: {obs2.reward}")
    print(f"Step feedback: {obs2.feedback}")
    print(f"Step sub_scores: {obs2.sub_scores}")
    
except Exception as e:
    print(f"CRASH: {e}")
    traceback.print_exc()
