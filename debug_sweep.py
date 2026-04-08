import subprocess
import time
import os
import threading

env = os.environ.copy()
env["PYTHONPATH"] = "."
env["ENV_BASE_URL"] = "http://localhost:8000"

# Write server output to a file instead of PIPE to avoid buffer deadlock.
# On Windows, subprocess.PIPE has a small buffer (~4KB). When the server
# prints enough debug output to fill it, print() blocks — which in turn
# blocks uvicorn's async event loop and prevents HTTP responses.
server_log_path = os.path.join(os.path.dirname(__file__), "server_debug.log")
server_log = open(server_log_path, "w")

print("Starting server...")
server = subprocess.Popen(
    ["py", "-3.12", "-m", "uvicorn", "server.app:app", "--port", "8000"],
    stdout=server_log,
    stderr=subprocess.STDOUT,
    text=True,
    env=env,
)

print("Waiting 30s for server to start...")
time.sleep(30)

try:
    print("--- RUNNING INFERENCE ---")
    result = subprocess.run(
        ["py", "-3.12", "inference.py"],
        capture_output=True,
        text=True,
        env=env,
    )
    print("STDOUT:")
    print(result.stdout)
    print("STDERR:")
    print(result.stderr)
finally:
    print("Terminating server...")
    server.terminate()
    try:
        server.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server.kill()
        print("Server killed after timeout.")
    server_log.close()

    # Now read and print the server log
    print("--- SERVER LOGS ---")
    with open(server_log_path, "r") as f:
        print(f.read())
