"""GriefBot Retirement Service — FastAPI application entry point."""

from __future__ import annotations

import os
import sys

# ---------------------------------------------------------------------------
# Path manipulation so flat imports work when run from the repo root
# (e.g. `PYTHONPATH=. uvicorn server.app:app`)
# ---------------------------------------------------------------------------
_here = os.path.dirname(os.path.abspath(__file__))
_parent = os.path.dirname(_here)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

# ---------------------------------------------------------------------------
# Imports — try flat first, then relative
# ---------------------------------------------------------------------------
try:
    from models import GriefBotAction, GriefBotObservation, GriefBotState
    from server.griefbot_environment import GriefBotEnvironment
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from models import GriefBotAction, GriefBotObservation, GriefBotState
    from server.griefbot_environment import GriefBotEnvironment

from fastapi import Request
from openenv_core.env_server.http_server import create_app


# ---------------------------------------------------------------------------
# Create the FastAPI app
# ---------------------------------------------------------------------------
app = create_app(
    env=GriefBotEnvironment,
    action_cls=GriefBotAction,
    observation_cls=GriefBotObservation,
    max_concurrent_envs=4,
)

from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <h1>🕊️ GriefBot Retirement Service</h1>
    <p>API is running successfully 🚀</p>
    """
# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------
def main(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Run the GriefBot Retirement Service locally."""
    import uvicorn

    uvicorn.run(app, host=host, port=port)


# Alias so validator can also discover `_run()` → `main()`
def _run() -> None:
    main()


if __name__ == "__main__":
    main()
