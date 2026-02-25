"""speednik/stages/hillside.py — Stage 1: Hillside Rush loader.

Delegates to the unified level loader.
"""

from __future__ import annotations

from speednik.level import StageData, load_stage


def load() -> StageData:
    """Load Hillside Rush stage data from pipeline JSON output."""
    return load_stage("hillside")
