"""speednik/scenarios/compare — Baseline comparison and regression detection."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from speednik.scenarios.runner import ScenarioOutcome


# ---------------------------------------------------------------------------
# Metric directionality
# ---------------------------------------------------------------------------

METRIC_DIRECTION: dict[str, str] = {
    "completion_time": "lower",
    "max_x": "higher",
    "rings_collected": "higher",
    "death_count": "lower",
    "total_reward": "higher",
    "average_speed": "higher",
    "peak_speed": "higher",
    "time_on_ground": "neutral",
    "stuck_at": "neutral",
}


def is_regression(
    metric: str, old_val: float, new_val: float, threshold: float = 0.05,
) -> bool:
    """Check if a metric change is a regression beyond *threshold*.

    Returns ``False`` for neutral metrics, unknown metrics, or changes
    within the threshold.
    """
    direction = METRIC_DIRECTION.get(metric, "neutral")
    if direction == "neutral":
        return False
    if old_val == 0:
        return False
    delta_pct = (new_val - old_val) / abs(old_val)
    if direction == "higher":
        return delta_pct < -threshold
    return delta_pct > threshold


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _pct_change(old_val: float, new_val: float) -> str:
    """Return a formatted percentage-change string like ``(+12.1%)``."""
    if old_val == 0:
        return "(N/A)"
    pct = (new_val - old_val) / abs(old_val) * 100
    return f"({pct:+.1f}%)"


def _annotation(
    metric: str, old_val: float, new_val: float, threshold: float,
) -> str:
    """Return an annotation string for a metric delta.

    Examples: ``"  ✓ faster"``, ``"  ⚠ regression"``, ``""``.
    """
    direction = METRIC_DIRECTION.get(metric, "neutral")
    if direction == "neutral":
        return ""
    if old_val == 0:
        return ""
    delta_pct = (new_val - old_val) / abs(old_val)

    # Improvement
    if direction == "higher" and delta_pct > threshold:
        return "  ✓ improved"
    if direction == "lower" and delta_pct < -threshold:
        return "  ✓ faster"

    # Regression
    if direction == "higher" and delta_pct < -threshold:
        return "  ⚠ regression"
    if direction == "lower" and delta_pct > threshold:
        return "  ⚠ slower"

    return ""


def _format_val(val: object) -> str:
    """Format a metric value for display."""
    if val is None:
        return "None"
    if isinstance(val, int):
        return str(val)
    if isinstance(val, float):
        if val == int(val) and abs(val) < 1e9:
            return f"{val:.1f}"
        return f"{val:.1f}"
    return str(val)


# ---------------------------------------------------------------------------
# Status changes
# ---------------------------------------------------------------------------


def _format_status_changes(
    current_by_name: dict[str, ScenarioOutcome],
    baseline_by_name: dict[str, dict],
) -> tuple[list[str], bool]:
    """Detect and format pass/fail status flips.

    Returns ``(lines, has_pass_to_fail)`` where *has_pass_to_fail* is True
    if any scenario flipped from PASS to FAIL.
    """
    lines: list[str] = []
    has_pass_to_fail = False

    all_names = sorted(set(current_by_name) | set(baseline_by_name))
    for name in all_names:
        cur = current_by_name.get(name)
        base = baseline_by_name.get(name)
        if cur is None or base is None:
            continue
        cur_status = "PASS" if cur.success else "FAIL"
        base_status = "PASS" if base["success"] else "FAIL"
        if cur_status != base_status:
            if base_status == "PASS" and cur_status == "FAIL":
                lines.append(f"  {name}: {base_status} → {cur_status}  (REGRESSION)")
                has_pass_to_fail = True
            else:
                lines.append(f"  {name}: {base_status} → {cur_status}  (fixed!)")

    return lines, has_pass_to_fail


# ---------------------------------------------------------------------------
# Per-scenario metric comparison
# ---------------------------------------------------------------------------


def _format_scenario_metrics(
    name: str,
    current_metrics: dict,
    baseline_metrics: dict,
    threshold: float,
) -> tuple[list[str], bool]:
    """Format metric deltas for one scenario.

    Returns ``(lines, has_regression)`` where *has_regression* is True if
    any metric regressed beyond the threshold.
    """
    shared = sorted(set(current_metrics) & set(baseline_metrics))
    lines: list[str] = []
    has_regression = False

    for key in shared:
        old_val = baseline_metrics[key]
        new_val = current_metrics[key]

        # Skip non-numeric / list metrics
        if isinstance(old_val, list) or isinstance(new_val, list):
            continue

        # Handle None values
        if old_val is None or new_val is None:
            lines.append(f"  {key:<20s}  {_format_val(old_val):>8s} → {_format_val(new_val)}")
            continue

        pct_str = _pct_change(old_val, new_val)
        ann = _annotation(key, old_val, new_val, threshold)
        lines.append(
            f"  {key:<20s}  {_format_val(old_val):>8s} → {_format_val(new_val):<8s} {pct_str}{ann}"
        )

        if is_regression(key, old_val, new_val, threshold):
            has_regression = True

    return lines, has_regression


# ---------------------------------------------------------------------------
# Main comparison entry point
# ---------------------------------------------------------------------------


def compare_results(
    current: list[ScenarioOutcome],
    baseline_path: Path | str,
    threshold: float = 0.05,
) -> int:
    """Load a baseline JSON and print a comparison against current results.

    Returns an exit code:
    - ``0``: no regressions
    - ``1``: a scenario flipped from PASS to FAIL
    - ``2``: significant metric regressions (above threshold) but no status flips
    """
    baseline_path = Path(baseline_path)
    with open(baseline_path) as f:
        baseline_data = json.load(f)

    baseline_by_name: dict[str, dict] = {e["name"]: e for e in baseline_data}
    current_by_name: dict[str, ScenarioOutcome] = {o.name: o for o in current}

    # --- Status changes ---
    status_lines, has_pass_to_fail = _format_status_changes(
        current_by_name, baseline_by_name,
    )
    if status_lines:
        header = "⚠ STATUS CHANGES:" if has_pass_to_fail else "STATUS CHANGES:"
        print(header)
        for line in status_lines:
            print(line)
        print()

    # --- Per-scenario metric diffs ---
    any_regression = False
    all_names = sorted(set(current_by_name) | set(baseline_by_name))

    for name in all_names:
        cur = current_by_name.get(name)
        base = baseline_by_name.get(name)

        if cur is None:
            print(f"{name}: MISSING (in baseline but not in current run)")
            continue

        if base is None:
            print(f"{name}: NEW (not in baseline)")
            continue

        current_metrics = cur.metrics
        baseline_metrics = base.get("metrics", {})

        metric_lines, has_regression = _format_scenario_metrics(
            name, current_metrics, baseline_metrics, threshold,
        )
        if has_regression:
            any_regression = True

        if metric_lines:
            print(f"{name}:")
            for line in metric_lines:
                print(line)

    # --- Exit code ---
    if has_pass_to_fail:
        return 1
    if any_regression:
        return 2
    return 0
