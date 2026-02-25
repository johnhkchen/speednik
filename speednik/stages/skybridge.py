"""speednik/stages/skybridge.py — Stage 3: Skybridge Gauntlet loader.

Delegates to the unified level loader.
"""

from __future__ import annotations

from speednik.level import StageData, load_stage


def load() -> StageData:
    """Load Skybridge Gauntlet stage data from pipeline JSON output."""
    return load_stage("skybridge")
