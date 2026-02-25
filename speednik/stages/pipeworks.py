"""speednik/stages/pipeworks.py — Stage 2: Pipe Works loader.

Delegates to the unified level loader.
"""

from __future__ import annotations

from speednik.level import StageData, load_stage


def load() -> StageData:
    """Load Pipe Works stage data from pipeline JSON output."""
    return load_stage("pipeworks")
