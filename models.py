"""GriefBot Retirement Service — Data models for the OpenEnv environment."""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from openenv_core.env_server.types import Action, Observation, State


class GriefBotAction(Action):
    """Action space for the GriefBot Retirement environment.

    Each action targets one of three tasks and carries the relevant payload.
    """

    task: Literal["chat_analysis", "farewell_convo", "memory_artifact"]
    analysis: Optional[Dict] = None  # For chat_analysis task
    farewell_messages: Optional[List[Dict[str, str]]] = None  # For farewell_convo task
    artifact: Optional[Dict] = None  # For memory_artifact task


class GriefBotObservation(Observation):
    """Observation returned after each step or reset."""

    task: str
    scenario: Dict
    feedback: str = ""
    sub_scores: Dict[str, float] = {}
    step_count: int = 0
    max_steps: int = 3
    done: bool = False
    reward: float = 0.0
    metadata: Dict = {}


class GriefBotState(State):
    """Internal environment state."""

    task: str = "chat_analysis"
    scenario: Dict = {}
    last_action: Optional[Dict] = None
    cumulative_reward: float = 0.0
    attempts: int = 0
