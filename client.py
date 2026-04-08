"""GriefBot Retirement Service — OpenEnv client wrapper."""

from __future__ import annotations

from typing import Any, Dict

from openenv_core.env_client import EnvClient

from models import GriefBotAction, GriefBotObservation, GriefBotState


class GriefBotEnv(EnvClient[GriefBotAction, GriefBotObservation, GriefBotState]):
    """Client for interacting with the GriefBot Retirement Service environment."""

    def _step_payload(self, action: GriefBotAction) -> Dict[str, Any]:
        """Serialize action for the /step endpoint."""
        return action.model_dump(exclude_none=True)

    def _parse_result(self, payload: Dict[str, Any]) -> GriefBotObservation:
        """Deserialize observation from the API response."""
        return GriefBotObservation(**payload)

    def _parse_state(self, payload: Dict[str, Any]) -> GriefBotState:
        """Deserialize state from the API response."""
        return GriefBotState(**payload)
