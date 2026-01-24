"""Command-line entrypoint for running the audit pipeline without uvicorn.

Example:
    python cli.py --url https://example.com
"""

import argparse
import json
import sys
from typing import Any, Dict

from .tasks import run_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run audit pipeline once and print JSON output."
    )
    parser.add_argument("--url", required=True, help="Page URL to audit")
    args = parser.parse_args()

    try:
        bundle, issues = run_pipeline(args.url)
    except Exception as exc:  # noqa: BLE001
        print(f"Pipeline failed: {exc}", file=sys.stderr)
        return 1

    output: Dict[str, Any] = {
        "bundle": bundle.model_dump(),
        "issues": issues,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
