"""speednik/scenarios/output — Console output and JSON serialization."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from speednik.scenarios.runner import ScenarioOutcome


# ---------------------------------------------------------------------------
# TTY / color helpers
# ---------------------------------------------------------------------------

_GREEN = "\033[32m"
_RED = "\033[31m"
_RESET = "\033[0m"


def _is_tty() -> bool:
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def _colorize(text: str, color: str) -> str:
    if _is_tty():
        return f"{color}{text}{_RESET}"
    return text


# ---------------------------------------------------------------------------
# Console output
# ---------------------------------------------------------------------------


def print_outcome(outcome: ScenarioOutcome) -> None:
    """Print a one-line pass/fail summary for a scenario outcome."""
    if outcome.success:
        status = _colorize("PASS", _GREEN)
    else:
        status = _colorize("FAIL", _RED)

    parts = [
        f"{status}  {outcome.name:<25s}",
        f"{outcome.frames_elapsed:>5d} frames",
        f"{outcome.wall_time_ms:>7.1f}ms",
    ]

    # Key metrics
    metrics = outcome.metrics
    if "max_x" in metrics:
        parts.append(f"max_x={metrics['max_x']:.1f}")
    if metrics.get("stuck_at") is not None:
        parts.append(f"stuck_at={metrics['stuck_at']:.1f}")

    print("  ".join(parts))


def print_summary(results: list[ScenarioOutcome]) -> None:
    """Print a summary line with pass/fail counts."""
    total = len(results)
    passed = sum(1 for r in results if r.success)
    failed = total - passed

    pass_str = f"{passed} passed"
    fail_str = f"{failed} failed"

    if _is_tty():
        pass_str = _colorize(pass_str, _GREEN) if passed else pass_str
        fail_str = _colorize(fail_str, _RED) if failed else fail_str

    print(f"\n{total} scenarios: {pass_str}, {fail_str}")


# ---------------------------------------------------------------------------
# JSON serialization
# ---------------------------------------------------------------------------


def _outcome_to_dict(
    outcome: ScenarioOutcome, include_trajectory: bool = False,
) -> dict:
    """Convert a ScenarioOutcome to a JSON-serializable dict."""
    d = asdict(outcome)
    if not include_trajectory:
        d.pop("trajectory", None)
    return d


def save_results(
    results: list[ScenarioOutcome],
    path: Path | str,
    include_trajectory: bool = False,
) -> None:
    """Save scenario outcomes as a JSON file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [_outcome_to_dict(r, include_trajectory) for r in results]
    path.write_text(json.dumps(data, indent=2) + "\n")

