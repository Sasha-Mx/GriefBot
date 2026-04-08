import os
import sys
import json
import traceback
import requests
from typing import Dict, List, Any, Optional

try:
    from openai import OpenAI
except ImportError:
    print("[ERROR] openai package not installed. Please install it.")
    sys.exit(1)

# --- CONFIGURATION ---
MODEL_NAME = os.getenv("MODEL_NAME", "meta-llama/Llama-3.3-70B-Instruct")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1/")
ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:8000")
HF_TOKEN = os.getenv("HF_TOKEN")
MAX_STEPS = 3

client = OpenAI(
    api_key=HF_TOKEN or "dummy_key",
    base_url=API_BASE_URL,
)

SYSTEM_PROMPTS = {
    "chat_analysis": "You are an AI relationship analyst. Analyze the provided chat history ('chat_excerpt') between a user and a GriefBot. Identify key themes and life milestones mentioned in the conversation. Also determine the emotional arc and the bot's personality traits (e.g. empathetic, patient). Return JSON like: {\"analysis\": {\"themes\": [\"grief\", \"loneliness\"], \"milestones\": [\"first job offer\"], \"emotional_arc\": \"despair to resilience\", \"bot_personality\": \"empathetic\"}}",
    "farewell_convo": "You are Aria, an empathetic AI companion saying goodbye to user Alex. Write a farewell DIALOGUE with EXACTLY 4 or more messages alternating between bot and user. The conversation should reference shared milestones (father's death, first job offer, failed exam). Ensure Alex feels empowered to move on — do NOT encourage them to come back. Include closure words like 'goodbye' or 'farewell'. Return JSON like: {\"farewell_messages\": [{\"role\": \"bot\", \"content\": \"...\"}, {\"role\": \"user\", \"content\": \"...\"}, {\"role\": \"bot\", \"content\": \"...\"}, {\"role\": \"user\", \"content\": \"...\"}]}",
    "memory_artifact": "You are a memory archivist for GriefBot Retirement Service. Create a memory artifact for user Alex based on the bot Aria's memory data. Include a title, a timeline of events (list of strings), key highlights (string), lessons learned (list of at least 3 strings), and a final closing letter from the bot Aria. IMPORTANT: In the closing_letter, Aria MUST describe her personality using the words 'empathetic', 'patient', and 'encouraging' — e.g. 'As your empathetic, patient, and encouraging companion...'. Also include bot_voice_sample (string description). Return JSON with keys: title, timeline, highlights, lessons, closing_letter, bot_voice_sample."
}

def call_llm(system_prompt: str, user_prompt: str) -> str:
    """Direct call to an OpenAI-compatible API."""
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.1,
        max_tokens=1500
    )
    return response.choices[0].message.content

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

def wrap_action(task: str, action_data: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure action_data matches expected fields without the 'action' wrapper."""
    result = {"task": task}
    
    if task == "chat_analysis":
        analysis = action_data.get("analysis") or action_data.get("chat_analysis") or action_data
        result["analysis"] = analysis
    elif task == "farewell_convo":
        farewell_messages = action_data.get("farewell_messages") or \
                            action_data.get("farewell_convo") or \
                            action_data.get("messages") or \
                            action_data
        if isinstance(farewell_messages, dict) and "content" in farewell_messages:
            farewell_messages = [farewell_messages]
        elif isinstance(farewell_messages, dict):
            farewell_messages = farewell_messages.get("farewell_messages") or \
                                farewell_messages.get("messages") or \
                                [farewell_messages]
        result["farewell_messages"] = farewell_messages
    elif task == "memory_artifact":
        artifact = action_data.get("memory_artifact") or action_data.get("artifact") or action_data
        result["artifact"] = artifact
    else:
        result.update(action_data)
        
    return result

def run_task(task: str) -> Dict[str, Any]:
    """Run a single task against the environment using raw requests."""
    print(f"[START] task={task} env=griefbot_retirement model={MODEL_NAME}")
    
    step_rewards = []
    best_score = 0.0
    total_steps = 0
    final_error = "null"
    success = "false"
    
    # 1. Reset
    try:
        req_headers = {"Connection": "close"}
        r = requests.post(f"{ENV_BASE_URL}/reset", json={"task": task, "episode_id": f"inference_{task}"}, headers=req_headers, timeout=15)
        r.raise_for_status()
        obs_full = r.json()
        obs = obs_full.get("observation", obs_full)
        scenario = obs.get("scenario", {})
    except Exception as e:
        final_error = f"reset_failed: {str(e)}"
        print(f"[END] success=false steps=0 score=0.0 rewards=0.0")
        return {"task": task, "success": False, "score": 0.0}

    # 2. Logic loop (max 3 steps as per env)
    for step_idx in range(1, MAX_STEPS + 1):
        total_steps = step_idx
        
        # LLM Call
        system_prompt = SYSTEM_PROMPTS[task]
        known_themes = scenario.get("known_themes", scenario.get("themes", []))
        known_milestones = scenario.get("known_milestones", scenario.get("milestones", []))
        
        user_prompt = (
            f"DATA FOR ANALYSIS/GENERATION:\n{json.dumps(scenario, indent=2)}\n\n"
            f"CONTEXT (Known information to help matching):\n"
            f"- Potential Themes: {known_themes}\n"
            f"- Potential Milestones: {known_milestones}\n\n"
            f"INSTRUCTIONS:\n"
            f"1. Extract the relationship themes and milestones from the chat data.\n"
            f"2. Use the provided context terms where applicable to ensure accuracy.\n"
            f"3. Return ONLY a valid JSON object matching the requested format.\n"
        )
        
        try:
            raw_response = call_llm(system_prompt, user_prompt)
            action_raw = parse_json_response(raw_response)
            action_data = wrap_action(task, action_raw)
            
            # Step
            payload = action_data.copy()
            payload["episode_id"] = f"inference_{task}"
            
            r = requests.post(f"{ENV_BASE_URL}/step", json=payload, headers={"Connection": "close"}, timeout=60)
            r.raise_for_status()
            result = r.json()
            
            reward = result.get("reward", 0.0)
            done = str(result.get("done", False)).lower()
            step_rewards.append(reward)
            best_score = max(best_score, reward)
            
            action_str = json.dumps(action_data, separators=(',', ':'))[:80]
            print(f"[STEP] step={step_idx} action={action_str} reward={reward:.2f} done={done} error=null")
            
            if result.get("done", False) or reward >= 0.95:
                success = "true" if best_score >= 0.5 else "false"
                break
                
        except Exception as e:
            final_error = f"step_failed: {str(e)}"
            action_str = json.dumps({"task": task, "error": "failed"}, separators=(',', ':'))[:80]
            print(f"[STEP] step={step_idx} action={action_str} reward=0.00 done=true error='{final_error}'")
            break

    rewards_str = ",".join([f"{r:.2f}" for r in step_rewards]) if step_rewards else "0.0"
    success = "true" if best_score >= 0.5 else "false"
    print(f"[END] success={success} steps={total_steps} score={best_score:.2f} rewards={rewards_str}")
    
    return {
        "task": task,
        "success": best_score >= 0.5,
        "score": best_score
    }

def main():
    target_task = os.environ.get("GRIEFBOT_TASK")
    tasks_to_run = [target_task] if target_task else ["chat_analysis", "farewell_convo", "memory_artifact"]
    
    overall_results = []
    for t in tasks_to_run:
        res = run_task(t)
        overall_results.append(res)
        
    print("\n" + "="*40, file=sys.stderr)
    print("FINAL SWEEP RESULTS", file=sys.stderr)
    print("="*40, file=sys.stderr)
    for res in overall_results:
        status = "PASSED" if res["success"] else "FAILED"
        print(f"{res['task'].ljust(18)}: {status} (Score: {res['score']:.2f})", file=sys.stderr)
    print("="*40, file=sys.stderr)

if __name__ == "__main__":
    main()
