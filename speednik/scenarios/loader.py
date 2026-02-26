"""speednik/scenarios/loader — ScenarioDef and YAML loading functions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from speednik.scenarios.conditions import (
    VALID_FAILURE_TYPES,
    VALID_SUCCESS_TYPES,
    FailureCondition,
    StartOverride,
    SuccessCondition,
)


@dataclass
class ScenarioDef:
    name: str
    description: str
    stage: str
    agent: str
    agent_params: dict | None
    max_frames: int
    success: SuccessCondition
    failure: FailureCondition
    metrics: list[str]
    start_override: StartOverride | None = None


def _parse_success(data: dict) -> SuccessCondition:
    """Parse a success condition dict into a SuccessCondition."""
    ctype = data["type"]
    if ctype not in VALID_SUCCESS_TYPES:
        raise ValueError(f"Unknown success condition type: {ctype!r}")
    return SuccessCondition(
        type=ctype,
        value=data.get("value"),
        min_speed=data.get("min_speed"),
    )


def _parse_failure(data: dict) -> FailureCondition:
    """Parse a failure condition dict into a FailureCondition."""
    ctype = data["type"]
    if ctype not in VALID_FAILURE_TYPES:
        raise ValueError(f"Unknown failure condition type: {ctype!r}")
    nested = None
    if ctype == "any":
        raw_conditions = data.get("conditions", [])
        nested = [_parse_failure(c) for c in raw_conditions]
    return FailureCondition(
        type=ctype,
        tolerance=data.get("tolerance"),
        window=data.get("window"),
        conditions=nested,
    )


def _parse_start_override(data: dict | None) -> StartOverride | None:
    """Parse an optional start_override dict."""
    if data is None:
        return None
    return StartOverride(x=float(data["x"]), y=float(data["y"]))


def _parse_scenario(data: dict) -> ScenarioDef:
    """Parse a raw YAML dict into a ScenarioDef."""
    return ScenarioDef(
        name=data["name"],
        description=data.get("description", ""),
        stage=data["stage"],
        agent=data["agent"],
        agent_params=data.get("agent_params"),
        max_frames=int(data["max_frames"]),
        success=_parse_success(data["success"]),
        failure=_parse_failure(data["failure"]),
        metrics=data.get("metrics", []),
        start_override=_parse_start_override(data.get("start_override")),
    )


def load_scenario(path: Path) -> ScenarioDef:
    """Load a single scenario from a YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)
    return _parse_scenario(data)


def load_scenarios(
    paths: list[Path] | None = None,
    run_all: bool = False,
    base: Path = Path("scenarios"),
) -> list[ScenarioDef]:
    """Load multiple scenarios.

    Args:
        paths: Explicit list of YAML file paths to load.
        run_all: If True, glob all ``*.yaml`` files under *base*.
        base: Directory to search when *run_all* is True.

    Returns:
        List of parsed ScenarioDef objects.
    """
    if paths is None:
        paths = []
    if run_all:
        paths = sorted(base.glob("*.yaml"))
    return [load_scenario(p) for p in paths]
