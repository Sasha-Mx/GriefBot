"""GriefBot Retirement Service — Core environment implementation."""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, Optional

# Ensure parent dir is on path for flat imports
_here = os.path.dirname(os.path.abspath(__file__))
_parent = os.path.dirname(_here)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from openenv_core.env_server import Environment

try:
    from models import GriefBotAction, GriefBotObservation, GriefBotState
    from tasks import SCENARIOS, TASK_NAMES, grade, get_observable_scenario
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from models import GriefBotAction, GriefBotObservation, GriefBotState
    from tasks import SCENARIOS, TASK_NAMES, grade, get_observable_scenario


class GriefBotEnvironment(Environment):
    """OpenEnv environment for the GriefBot Retirement Service.

    Agents learn to gracefully retire AI companion chatbots by:
      1. Analyzing chat relationships
      2. Writing farewell conversations
      3. Generating memory artifacts
    """

    SUPPORTS_CONCURRENT_SESSIONS = True
    MAX_STEPS = 3

    def __init__(self) -> None:
        super().__init__()
        self._task: str = "chat_analysis"
        self._scenario: Dict = {}
        self._step_count: int = 0
        self._cumulative_reward: float = 0.0
        self._last_action: Optional[Dict] = None
        self._done: bool = False
        self._last_feedback: str = ""
        self._last_sub_scores: Dict[str, float] = {}
        self._last_reward: float = 0.0

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs: Any,
    ) -> GriefBotObservation:
        """Reset the environment, optionally selecting a specific task."""
        # Robustly pull task from kwargs (since it's no longer in the signature)
        requested_task = kwargs.get("task")
        
        self._task = requested_task if requested_task and requested_task in TASK_NAMES else "chat_analysis"
        self._scenario = get_observable_scenario(self._task)
        self._step_count = 0
        self._cumulative_reward = 0.0
        self._last_action = None
        self._done = False
        self._last_feedback = f"Task '{self._task}' initialized. Submit your action."
        self._last_sub_scores = {}
        self._last_reward = 0.0

        return GriefBotObservation(
            task=self._task,
            scenario=self._scenario,
            feedback=self._last_feedback,
            sub_scores={},
            step_count=0,
            max_steps=self.MAX_STEPS,
            done=False,
            reward=0.0,
            metadata={"episode_id": episode_id or "", "seed": seed},
        )

    def step(self, action: GriefBotAction, **kwargs) -> GriefBotObservation:
        """Process one agent action and return graded observation."""
        self._step_count += 1
        self._last_action = action.model_dump(exclude_none=True)

        # Robustly synchronize task context from action if needed
        if action.task and action.task != self._task and action.task in TASK_NAMES:
            self._task = action.task
            self._scenario = get_observable_scenario(self._task)

        # Final validate (should now match if action.task was valid)
        if action.task != self._task:
            self._last_feedback = (
                f"Task mismatch: expected '{self._task}', got '{action.task}'."
            )
            self._last_sub_scores = {}
            self._last_reward = 0.0
            done = self._step_count >= self.MAX_STEPS
            self._done = done
            return GriefBotObservation(
                task=self._task,
                scenario=self._scenario,
                feedback=self._last_feedback,
                sub_scores={},
                step_count=self._step_count,
                max_steps=self.MAX_STEPS,
                done=done,
                reward=0.0,
                metadata={"error": "task_mismatch"},
            )

        # Grade the action
        reward, sub_scores, feedback = grade(self._task, self._last_action)

        self._last_reward = reward
        self._last_sub_scores = sub_scores
        self._last_feedback = feedback
        self._cumulative_reward = max(self._cumulative_reward, reward)

        done = self._step_count >= self.MAX_STEPS or reward >= 0.95
        self._done = done

        return GriefBotObservation(
            task=self._task,
            scenario=self._scenario,
            feedback=feedback,
            sub_scores=sub_scores,
            step_count=self._step_count,
            max_steps=self.MAX_STEPS,
            done=done,
            reward=reward,
            metadata={
                "cumulative_reward": self._cumulative_reward,
                "attempts": self._step_count,
            },
        )

    @property
    def state(self) -> GriefBotState:
        """Return the current environment state."""
        return GriefBotState(
            task=self._task,
            scenario=self._scenario,
            last_action=self._last_action,
            cumulative_reward=self._cumulative_reward,
            attempts=self._step_count,
        )
