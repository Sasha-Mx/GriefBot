import subprocess
import time
import os
import signal

env = os.environ.copy()
env["PYTHONPATH"] = "."
# HF_TOKEN should be set in environment or .env
# env["HF_TOKEN"] = "redacted"
env["GRIEFBOT_TASK"] = "farewell_convo"
env["ENV_BASE_URL"] = "http://localhost:8000"

print("Starting server...")
server = subprocess.Popen(
    ["py", "-3.12", "-m", "uvicorn", "server.app:app", "--port", "8000"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    env=env
)

time.sleep(15)

try:
    print("--- RUNNING INFERENCE ---")
    result = subprocess.run(
        ["py", "-3.12", "inference.py"],
        capture_output=True,
        text=True,
        env=env
    )
    print("STDOUT:")
    print(result.stdout)
    print("STDERR:")
    print(result.stderr)
finally:
    print("Terminating server...")
    server.terminate()
    try:
        out, _ = server.communicate(timeout=5)
        print("--- SERVER LOGS ---")
        print(out)
    except subprocess.TimeoutExpired:
        server.kill()
        print("Server killed after timeout.")
