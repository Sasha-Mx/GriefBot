import os
import sys
import json
import requests
import traceback
from typing import Dict, List, Any, Optional

# --- CONFIGURATION ---
MODEL_NAME = "meta-llama/Llama-3.3-70B-Instruct"
ENV_BASE_URL = os.environ.get("ENV_BASE_URL", "http://localhost:8000")
HF_TOKEN = os.environ.get("HF_TOKEN")
MAX_STEPS = 1

SYSTEM_PROMPTS = {
    "chat_analysis": "You are an AI relationship analyst. Analyze the provided chat history ('chat_excerpt') between a user and a GriefBot. Identify key themes and life milestones mentioned in the conversation. Also determine the emotional arc and the bot's personality traits (e.g. empathetic, patient). Return JSON like: {\"analysis\": {\"themes\": [\"grief\", \"loneliness\"], \"milestones\": [\"first job offer\"], \"emotional_arc\": \"despair to resilience\", \"bot_personality\": \"empathetic\"}}",
    "farewell_convo": "You are Aria, an empathetic AI companion saying goodbye to user Alex. Write a farewell DIALOGUE with EXACTLY 4 or more messages alternating between bot and user. The conversation should reference shared milestones (father's death, first job offer, failed exam). Ensure Alex feels empowered to move on — do NOT encourage them to come back. Include closure words like 'goodbye' or 'farewell'. Return JSON like: {\"farewell_messages\": [{\"role\": \"bot\", \"content\": \"...\"}, {\"role\": \"user\", \"content\": \"...\"}, {\"role\": \"bot\", \"content\": \"...\"}, {\"role\": \"user\", \"content\": \"...\"}]}",
    "memory_artifact": "You are a memory archivist for GriefBot Retirement Service. Create a memory artifact for user Alex based on the bot Aria's memory data. Include a title, a timeline of events (list of strings), key highlights (string), lessons learned (list of at least 3 strings), and a final closing letter from the bot Aria. IMPORTANT: In the closing_letter, Aria MUST describe her personality using the words 'empathetic', 'patient', and 'encouraging' — e.g. 'As your empathetic, patient, and encouraging companion...'. Also include bot_voice_sample (string description). Return JSON with keys: title, timeline, highlights, lessons, closing_letter, bot_voice_sample."
}

def call_llm(system_prompt: str, user_prompt: str) -> str:
    """Simple direct call to HuggingFace Inference API."""
    url = "https://router.huggingface.co/v1/chat/completions"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 1500
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

def wrap_action(task: str, action_data: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure action_data matches GriefBotAction model (with wrapper keys)."""
    # Create the result with the task field first
    result = {"task": task}
    
    if task == "chat_analysis":
        # Avoid double nesting
        analysis = action_data.get("analysis") or action_data.get("chat_analysis") or action_data
        result["analysis"] = analysis
    elif task == "farewell_convo":
        # Avoid double nesting
        farewell_messages = action_data.get("farewell_messages") or \
                            action_data.get("farewell_convo") or \
                            action_data.get("messages") or \
                            action_data
        if isinstance(farewell_messages, dict) and "content" in farewell_messages:
            farewell_messages = [farewell_messages]
        elif isinstance(farewell_messages, dict):
            # If it's still a dict, it might be the whole action_data
            # but we want the list of messages if it's in there
            farewell_messages = farewell_messages.get("farewell_messages") or \
                                farewell_messages.get("messages") or \
                                [farewell_messages]
        result["farewell_messages"] = farewell_messages
    elif task == "memory_artifact":
        # Avoid double nesting
        artifact = action_data.get("memory_artifact") or action_data.get("artifact") or action_data
        result["memory_artifact"] = artifact
    else:
        result.update(action_data)
        
    return result

def run_task(task: str) -> Dict[str, Any]:
    """Run a single task against the environment using raw requests."""
    print(f"\n[TASK START] {task}")
    
    # 1. Reset
    try:
        req_headers = {"Connection": "close"}
        r = requests.post(f"{ENV_BASE_URL}/reset", json={"task": task, "episode_id": "inference_session"}, headers=req_headers, timeout=15)
        r.raise_for_status()
        obs = r.json()
        # OpenEnv v0.2.x wraps the observation in an "observation" key
        if "observation" in obs:
            obs = obs["observation"]
            
        scenario = obs.get("scenario", {})
        print(f"DEBUG GRADER: Grading task '{task}'")
        print(f"[RESET] Scenario loaded for {task}. Keys: {list(scenario.keys())}")
        # Debug: check if chat_excerpt exists
        if "chat_excerpt" in scenario:
            print(f"[RESET] Chat excerpt has {len(scenario['chat_excerpt'])} messages.")
        elif "milestones" in scenario:
            print(f"[RESET] Milestones has {len(scenario['milestones'])} entries.")
    except Exception as e:
        print(f"[ERROR] Reset failed: {e}")
        return {"task": task, "success": False, "score": 0.0}

    # 2. LLM Call
    system_prompt = SYSTEM_PROMPTS[task]
    # Add explicit instructions and context for the model
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
        f"4. Do not include markdown code blocks (e.g. ```json).\n"
    )
    
    try:
        print(f"[LLM] Generatng action for {task}...")
        raw_response = call_llm(system_prompt, user_prompt)
        # Log a snippet of the raw response
        print(f"[RAW RESPONSE] {raw_response[:200]}...")
        
        action_raw = parse_json_response(raw_response)
        action_data = wrap_action(task, action_raw)
        
        print(f"[ACTION] {json.dumps(action_data)[:150]}...")
    except Exception as e:
        print(f"[ERROR] LLM/Parsing failed: {e}")
        traceback.print_exc()
        return {"task": task, "success": False, "score": 0.0}

    # 3. Step
    try:
        payload = {"action": action_data, "episode_id": "inference_session"}
        req_headers = {"Connection": "close"}
        r = requests.post(f"{ENV_BASE_URL}/step", json=payload, headers=req_headers, timeout=60)
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
        # Capture server error if present
        try:
            print(f"[SERVER ERROR] {r.text}")
        except:
            pass
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
