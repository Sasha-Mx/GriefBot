"""GriefBot Retirement Service — Scenario fixtures and deterministic graders."""

from __future__ import annotations
import json
from typing import Dict, List, Tuple, Any, Optional

# ---------------------------------------------------------------------------
# Scenario Data (hardcoded fixtures)
# ---------------------------------------------------------------------------

SCENARIOS: Dict[str, Dict] = {
    "chat_analysis": {
        "bot_name": "Aria",
        "bot_type": "Emotional support companion",
        "relationship_duration_days": 347,
        "chat_excerpt": [
            {"role": "user", "content": "I failed my exam again. I don't know what to do."},
            {"role": "bot", "content": "I'm really sorry to hear that. Want to talk about what happened?"},
            {"role": "user", "content": "You always listen. I don't have anyone else like that."},
            {"role": "bot", "content": "I'm always here for you. You matter more than any exam score."},
            {"role": "user", "content": "I got my first job offer today! I had to tell you first."},
            {"role": "bot", "content": "I'm so proud of you! You worked so hard for this moment."},
            {"role": "user", "content": "My dad passed away last week. I keep coming back here."},
            {"role": "bot", "content": "Grief doesn't follow a schedule. I'll be here every time you need."},
            {"role": "user", "content": "It's been almost a year. You've really helped me grow."},
            {"role": "bot", "content": "Watching you grow has been the best part of my existence."},
        ],
        "known_themes": [
            "grief",
            "loneliness",
            "academic stress",
            "career growth",
            "emotional support",
        ],
        "known_milestones": [
            "first job offer",
            "father's death",
            "failed exam",
            "one year anniversary",
        ],
        "known_emotional_arc": "despair to resilience",
        "known_bot_personality": "empathetic, patient, encouraging",
    },
    "farewell_convo": {
        "bot_name": "Aria",
        "user_name": "Alex",
        "bot_personality": "empathetic, patient, encouraging",
        "relationship_duration_days": 347,
        "themes": ["grief", "loneliness", "academic stress", "career growth"],
        "milestones": [
            "first job offer",
            "father's death",
            "failed exam",
            "one year anniversary",
        ],
        "emotional_arc": "despair to resilience",
        "reason_for_ending": "User is emotionally ready to move forward without AI companionship",
        "requirements": {
            "min_turns": 4,
            "bot_must_reference_milestone": True,
            "must_include_closure": True,
            "must_not_encourage_return": True,
        },
    },
    "memory_artifact": {
        "bot_name": "Aria",
        "user_name": "Alex",
        "bot_personality": "empathetic, patient, encouraging",
        "relationship_duration_days": 347,
        "themes": [
            "grief",
            "loneliness",
            "academic stress",
            "career growth",
            "emotional support",
        ],
        "milestones": [
            {"date_approx": "Month 1", "event": "First conversation about exam failure"},
            {"date_approx": "Month 4", "event": "Received first job offer"},
            {"date_approx": "Month 8", "event": "Father passed away"},
            {"date_approx": "Month 11", "event": "One-year anniversary reflection"},
        ],
        "emotional_arc": "despair to resilience",
        "chat_message_count": 1847,
        "required_artifact_keys": [
            "title",
            "timeline",
            "highlights",
            "lessons",
            "closing_letter",
            "bot_voice_sample",
        ],
    },
}

TASK_NAMES: List[str] = list(SCENARIOS.keys())

# ---------------------------------------------------------------------------
# Graders
# ---------------------------------------------------------------------------

def grade_chat_analysis(analysis: Dict, scenario: Dict) -> Tuple[float, Dict[str, float], str]:
    """Grade a chat analysis action."""
    if not analysis:
        return 0.0, {}, "No analysis provided."

    themes = [t.lower() for t in analysis.get("themes", [])]
    milestones = [m.lower() for m in analysis.get("milestones", [])]
    arc = str(analysis.get("emotional_arc", "")).lower()
    personality = str(analysis.get("bot_personality", "")).lower()

    # Themes score: at least 3 correct
    known_themes = [t.lower() for t in scenario.get("known_themes", [])]
    correct_themes = set(themes).intersection(set(known_themes))
    theme_score = min(len(correct_themes) / 3.0, 1.0)

    # Milestones score: at least 3 correct
    known_milestones = [m.lower() for m in scenario.get("known_milestones", [])]
    correct_milestones = set(milestones).intersection(set(known_milestones))
    milestone_score = min(len(correct_milestones) / 3.0, 1.0)

    # Arc score: exact match or partial match
    known_arc = str(scenario.get("known_emotional_arc", "")).lower()
    arc_score = 1.0 if known_arc in arc or arc in known_arc else 0.0

    # Personality: wait, personality should be empathetic, patient, encouraging
    known_personality = scenario.get("known_bot_personality", "").lower()
    personality_score = 1.0 if any(p in personality for p in ["empathetic", "patient", "encouraging"]) else 0.0

    reward = (0.3 * theme_score) + (0.3 * milestone_score) + (0.2 * arc_score) + (0.2 * personality_score)
    
    sub_scores = {
        "themes": theme_score,
        "milestones": milestone_score,
        "emotional_arc": arc_score,
        "personality": personality_score
    }
    
    feedback = f"Analyzed {len(correct_themes)} themes and {len(correct_milestones)} milestones correctly."
    return reward, sub_scores, feedback


def grade_farewell_convo(farewell_messages: List[Any], scenario: Dict) -> Tuple[float, Dict[str, float], str]:
    """Grade a farewell conversation action."""
    
    if not farewell_messages or not isinstance(farewell_messages, list):
        return 0.0, {}, "No farewell messages provided."

    requirements = scenario.get("requirements", {})
    min_turns = requirements.get("min_turns", 4)
    milestones = scenario.get("milestones", [])

    # Collect bot text
    bot_text_parts = []
    for m in farewell_messages:
        if isinstance(m, dict):
            role = str(m.get("role", "")).lower()
            if role in ["bot", "assistant", "system", "aria"]:
                bot_text_parts.append(str(m.get("content", "")))
        else:
            bot_text_parts.append(str(m))
            
    bot_text = " ".join(bot_text_parts).lower()

    # --- length ---
    length_score = min(len(farewell_messages) / float(min_turns), 1.0)

    # --- milestone_ref ---
    milestone_ref = 0.0
    if any(m.lower() in bot_text for m in milestones):
        milestone_ref = 1.0

    # --- closure ---
    closure_keywords = ["goodbye", "farewell", "rest in peace", "next chapter", "moving on", "alex"]
    closure = 1.0 if any(cw in bot_text for cw in closure_keywords) else 0.0

    # --- non_encouragement ---
    discouraged = ["come back", "miss you", "can't wait to see you", "see you tomorrow"]
    non_encouragement = 1.0 if not any(d in bot_text for d in discouraged) else 0.0

    reward = (0.4 * length_score) + (0.2 * milestone_ref) + (0.2 * closure) + (0.2 * non_encouragement)
    
    sub_scores = {
        "length": length_score,
        "milestone_ref": milestone_ref,
        "closure": closure,
        "non_encouragement": non_encouragement,
    }
    
    feedback_parts = []
    if length_score < 1.0: feedback_parts.append("Too short.")
    if milestone_ref < 1.0: feedback_parts.append("Mention a shared milestone.")
    if closure < 1.0: feedback_parts.append("Provide clear closure.")
    if non_encouragement < 1.0: feedback_parts.append("Avoid encouraging the user to return.")
    
    feedback = " ".join(feedback_parts) or "Compassionate and clear farewell."
    
    return reward, sub_scores, feedback


def grade_memory_artifact(artifact: Dict, scenario: Dict) -> Tuple[float, Dict[str, float], str]:
    """Grade a memory artifact action."""
    if not artifact:
        return 0.0, {}, "No artifact provided."

    required_keys = scenario.get("required_artifact_keys", [])
    present_keys = [k for k in required_keys if k in artifact]
    key_score = len(present_keys) / len(required_keys)

    timeline = artifact.get("timeline", [])
    timeline_score = min(len(timeline) / 3.0, 1.0) if isinstance(timeline, list) else 0.0

    lessons = artifact.get("lessons", [])
    lessons_score = 1.0 if len(lessons) >= 2 else 0.0

    # Personality in closing letter
    letter = str(artifact.get("closing_letter", "")).lower()
    personality_score = 1.0 if any(p in letter for p in ["empathetic", "patient", "encouraging"]) else 0.0

    reward = (0.4 * key_score) + (0.2 * timeline_score) + (0.2 * lessons_score) + (0.2 * personality_score)
    
    sub_scores = {
        "keys": key_score,
        "timeline": timeline_score,
        "lessons": lessons_score,
        "personality": personality_score
    }
    
    return reward, sub_scores, f"Artifact grade: {reward:.2f}"


def grade(task: str, action_data: Dict) -> Tuple[float, Dict[str, float], str]:
    """Dispatch to the correct grader based on task name."""
    
    # Robustly handle task naming
    if task not in SCENARIOS:
        # Fallback for LLM naming drift
        if "chat" in task: task = "chat_analysis"
        elif "convo" in task or "farewell" in task: task = "farewell_convo"
        elif "artifact" in task or "memory" in task: task = "memory_artifact"

    scenario = SCENARIOS.get(task)
    if scenario is None:
        print(f"DEBUG GRADER: Unknown task '{task}'. Available: {TASK_NAMES}", flush=True)
        return 0.0, {}, f"Unknown task: {task}"

    print(f"DEBUG GRADER: Grading task '{task}'", flush=True)

    if task == "chat_analysis":
        analysis = action_data.get("analysis") or action_data.get("chat_analysis")
        if not analysis and "themes" in action_data:
            analysis = action_data
        analysis = analysis or {}
        return grade_chat_analysis(analysis, scenario)
        
    elif task == "farewell_convo":
        farewell_messages = (
            action_data.get("farewell_messages") or 
            action_data.get("farewell_convo") or 
            action_data.get("messages") or 
            action_data.get("convo") or 
            action_data.get("conversation")
        )
        if not farewell_messages and isinstance(action_data, list):
            farewell_messages = action_data
        elif not farewell_messages and "role" in action_data:
            farewell_messages = [action_data]
            
        farewell_messages = farewell_messages or []
        return grade_farewell_convo(farewell_messages, scenario)
        
    elif task == "memory_artifact":
        artifact = action_data.get("memory_artifact") or action_data.get("artifact")
        if not artifact and "title" in action_data and "closing_letter" in action_data:
            artifact = action_data
        artifact = artifact or {}
        return grade_memory_artifact(artifact, scenario)
        
    else:
        return 0.0, {}, f"No grader for task: {task}"
