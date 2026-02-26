"""speednik/scenarios/cli — CLI entry point for running scenarios.

Usage::

    uv run python -m speednik.scenarios.cli scenarios/hillside_complete.yaml
    uv run python -m speednik.scenarios.cli --all
    uv run python -m speednik.scenarios.cli --all --agent hold_right
    uv run python -m speednik.scenarios.cli --all -o results/run_001.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from speednik.scenarios.loader import load_scenarios
from speednik.scenarios.compare import compare_results
from speednik.scenarios.output import print_outcome, print_summary, save_results
from speednik.scenarios.runner import run_scenario


def main(argv: list[str] | None = None) -> None:
    """Run scenarios from the command line."""
    parser = argparse.ArgumentParser(description="Run Speednik scenarios")
    parser.add_argument(
        "scenarios", nargs="*", help="Scenario YAML files",
    )
    parser.add_argument(
        "--all", action="store_true", help="Run all scenarios in scenarios/",
    )
    parser.add_argument(
        "--agent", help="Override agent for all scenarios",
    )
    parser.add_argument(
        "--output", "-o", help="Output file path for results JSON",
    )
    parser.add_argument(
        "--trajectory", action="store_true",
        help="Include per-frame trajectory in JSON output",
    )
    parser.add_argument(
        "--compare", help="Compare against baseline results JSON",
    )
    args = parser.parse_args(argv)

    # Must specify scenarios or --all
    if not args.scenarios and not args.all:
        parser.print_usage()
        sys.exit(2)

    paths = [Path(s) for s in args.scenarios] if args.scenarios else None
    scenario_defs = load_scenarios(paths=paths, run_all=args.all)

    results = []
    for scenario_def in scenario_defs:
        if args.agent:
            scenario_def.agent = args.agent
            scenario_def.agent_params = None
        outcome = run_scenario(scenario_def)
        results.append(outcome)
        print_outcome(outcome)

    print_summary(results)

    if args.output:
        save_results(results, args.output, include_trajectory=args.trajectory)

    if args.compare:
        exit_code = compare_results(results, args.compare)
        sys.exit(exit_code)

    if all(r.success for r in results):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
