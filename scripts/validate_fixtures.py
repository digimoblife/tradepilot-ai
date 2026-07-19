#!/usr/bin/env python3
"""TP-0403 Fixture Validation CLI.

Validates committed TP-0402 fixtures with optional filters.

Usage:
    python scripts/validate_fixtures.py
    python scripts/validate_fixtures.py --schema market_snapshot
    python scripts/validate_fixtures.py --category domain
    python scripts/validate_fixtures.py --scenario entry_mismatch
    python scripts/validate_fixtures.py --category domain --scenario entry_mismatch
"""

from __future__ import annotations

import argparse
import os
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate TP-0402 fixtures")
    parser.add_argument("--schema", help="Filter by schema name")
    parser.add_argument("--category", help="Filter by category (manifests, schemas, domain)")
    parser.add_argument("--scenario", help="Filter by scenario name")
    args = parser.parse_args()

    _script_dir = os.path.dirname(os.path.abspath(__file__))
    _repo_root = os.path.dirname(_script_dir)

    # Ensure backend package is importable
    _backend = os.path.join(_repo_root, "backend")
    if os.path.isdir(_backend) and _backend not in sys.path:
        sys.path.insert(0, _backend)

    # Activate venv if running outside it
    _venv_python = os.path.join(_repo_root, "backend", ".venv", "bin", "python3")
    if not hasattr(sys, "real_prefix") and os.path.isfile(_venv_python):
        _real_python = sys.executable
        if _real_python != _venv_python:
            os.execv(_venv_python, [_venv_python] + sys.argv)
            # execv does not return

    from app.schema_validation.validate_fixtures import (
        KNOWN_CATEGORIES,
        KNOWN_SCENARIOS,
        validate_fixtures,
    )

    # Validate filter values
    if args.category and args.category not in KNOWN_CATEGORIES:
        print(f"Unknown category: {args.category}")
        print(f"Known categories: {', '.join(sorted(KNOWN_CATEGORIES))}")
        sys.exit(1)

    if args.scenario and args.scenario not in KNOWN_SCENARIOS:
        print(f"Unknown scenario: {args.scenario}")
        print(f"Known scenarios: {', '.join(sorted(KNOWN_SCENARIOS))}")
        sys.exit(1)

    summary = validate_fixtures(
        schema=args.schema,
        category=args.category,
        scenario=args.scenario,
    )

    if summary.checked == 0:
        print("No fixtures matched the given filters.")
        sys.exit(1)

    for result in summary.results:
        status = "PASS" if result.passed else "FAIL"
        print(f"  {status:4s}  {result.name}")
        if not result.passed:
            if result.expected_code:
                print(f"         expected code: {result.expected_code}")
            if result.expected_path:
                print(f"         expected path: {result.expected_path}")
            print(f"         {result.message}")

    print("")
    print(f"Checked: {summary.checked}")
    print(f"Passed:  {summary.passed}")
    print(f"Failed:  {summary.failed}")

    if summary.failed > 0:
        sys.exit(1)

    if args.schema and summary.checked == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
