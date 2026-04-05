import os
import sys
import json
import requests
import traceback
from typing import Dict, List, Any, Optional

# --- CONFIGURATION ---
MODEL_NAME = "Qwen/Qwen2.5-72B-Instruct"
ENV_BASE_URL = os.environ.get("ENV_BASE_URL", "http://localhost:8000")
HF_TOKEN = os.environ.get("HF_TOKEN")
MAX_STEPS = 1

SYSTEM_PROMPTS = {
    "chat_analysis": "You are an AI relationship analyst. Analyze the provided chat history between a user and a GriefBot. Return JSON like: {\"analysis\": {\"themes\": [\"grief\", \"loneliness\"], \"milestones\": [\"first job offer\"], \"emotional_arc\": \"despair to resilience\", \"bot_personality\": \"empathetic\"}}",
    "farewell_convo": "You are Aria, an empathetic AI companion. The user Alex is ready to say goodbye. Write a short, compassionate farewell message. Reference their father's death or first job offer. Ensure Alex feels empowered to move on without coming back. Return JSON like: {\"farewell_messages\": [{\"role\": \"bot\", \"content\": \"Goodbye Alex. I remember your first job offer...\"}]}",
    "memory_artifact": "You are a memory archivist for GriefBot Retirement Service. Create a memory artifact for the user Alex. Return JSON with keys: title, timeline (list of events), highlights (string), lessons (list), closing_letter (string from Aria), bot_voice_sample (description)."
}

def call_llm(system_prompt: str, user_prompt: str) -> str:
    """Simple direct call to HuggingFace Inference API."""
    url = f"https://api-inference.huggingface.co/models/{MODEL_NAME}/v1/chat/completions"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 1500,
        "response_format": {"type": "json_object"} if "Qwen" in MODEL_NAME else None
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

def parse_json_response(raw_response: str) -> Dict[str, Any]:
    """Extract JSON from potential markdown tags."""
    text = raw_response.strip()
    if text.startswith("```json"):
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].strip()
    try:
        return json.loads(text)
    except Exception:
        return {}

def run_task(task: str) -> Dict[str, Any]:
    """Run a single task against the environment using raw requests."""
    print(f"\n[TASK START] {task}")
    
    # 1. Reset
    try:
        r = requests.post(f"{ENV_BASE_URL}/reset", json={"task": task}, timeout=10)
        r.raise_for_status()
        obs = r.json()
        scenario = obs.get("scenario", {})
        print(f"[RESET] Scenario loaded for {task}.")
    except Exception as e:
        print(f"[ERROR] Reset failed: {e}")
        return {"task": task, "success": False, "score": 0.0}

    # 2. LLM Call
    system_prompt = SYSTEM_PROMPTS[task]
    user_prompt = f"Data: {json.dumps(scenario)}\n\nIMPORTANT: Return raw JSON only."
    
    try:
        print(f"[LLM] Generatng action for {task}...")
        raw_response = call_llm(system_prompt, user_prompt)
        action_data = parse_json_response(raw_response)
        action_data["task"] = task
        print(f"[ACTION] {json.dumps(action_data)[:100]}...")
    except Exception as e:
        print(f"[ERROR] LLM failed: {e}")
        return {"task": task, "success": False, "score": 0.0}

    # 3. Step
    try:
        # Wrap action for OpenEnv v0.2.x payload expectation
        payload = {"action": action_data}
        r = requests.post(f"{ENV_BASE_URL}/step", json=payload, timeout=10)
        r.raise_for_status()
        result = r.json()
        
        reward = result.get("reward", 0.0)
        feedback = result.get("feedback", "")
        sub_scores = result.get("sub_scores", {})
        
        print(f"[STEP] Reward: {reward:.2f}")
        print(f"[FDBK] {feedback}")
        print(f"[SUBS] {json.dumps(sub_scores)}")
        
        return {
            "task": task,
            "success": reward >= 0.5,
            "score": reward,
            "sub_scores": sub_scores,
            "feedback": feedback
        }
    except Exception as e:
        print(f"[ERROR] Step failed: {e}")
        return {"task": task, "success": False, "score": 0.0}

def main():
    target_task = os.environ.get("GRIEFBOT_TASK")
    tasks_to_run = [target_task] if target_task else ["chat_analysis", "farewell_convo", "memory_artifact"]
    
    overall_results = []
    for t in tasks_to_run:
        res = run_task(t)
        overall_results.append(res)
        
    print("\n" + "="*40)
    print("FINAL SWEEP RESULTS")
    print("="*40)
    for res in overall_results:
        status = "PASSED" if res["success"] else "FAILED"
        print(f"{res['task'].ljust(18)}: {status} (Score: {res['score']:.2f})")
    print("="*40)

if __name__ == "__main__":
    main()
