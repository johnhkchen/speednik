"""speednik/scenarios — Scenario definition, loading, conditions, and runner (Layer 4)."""

from speednik.scenarios.conditions import (
    VALID_FAILURE_TYPES,
    VALID_SUCCESS_TYPES,
    FailureCondition,
    StartOverride,
    SuccessCondition,
    check_conditions,
)
from speednik.scenarios.loader import ScenarioDef, load_scenario, load_scenarios
from speednik.scenarios.runner import FrameRecord, ScenarioOutcome, run_scenario
from speednik.scenarios.compare import compare_results
from speednik.scenarios.output import print_outcome, print_summary, save_results

__all__ = [
    "VALID_SUCCESS_TYPES",
    "VALID_FAILURE_TYPES",
    "SuccessCondition",
    "FailureCondition",
    "StartOverride",
    "check_conditions",
    "ScenarioDef",
    "load_scenario",
    "load_scenarios",
    "FrameRecord",
    "ScenarioOutcome",
    "run_scenario",
    "print_outcome",
    "print_summary",
    "save_results",
    "compare_results",
]
