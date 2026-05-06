"""Command-line entry point.

Run with ``rpa --records ./samples/records.json``. Dry-run with ``--dry-run``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rpa_template.config import load_settings
from rpa_template.core.entities import Record
from rpa_template.flows.run import run


def _load_records(path: Path) -> list[Record]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [Record(key=item["key"], payload=item.get("payload", {})) for item in raw]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rpa")
    parser.add_argument(
        "--records",
        type=Path,
        required=True,
        help="Path to a JSON file with [{\"key\": str, \"payload\": dict}, ...]",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Traverse the flow without performing writes.",
    )
    args = parser.parse_args(argv)

    settings = load_settings()
    if args.dry_run:
        settings = settings.model_copy(update={"dry_run": True})

    records = _load_records(args.records)
    outcomes = run(settings, records)
    failed = [o for o in outcomes if o.status == "error"]
    return 1 if failed else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
