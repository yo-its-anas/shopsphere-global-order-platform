#!/usr/bin/env python3
"""Validate the order-service Alembic revision graph without a database connection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    repository_root = Path(__file__).resolve().parents[1]
    service_directory = repository_root / "services" / "order-service"
    configuration = Config(str(service_directory / "alembic.ini"))
    configuration.set_main_option(
        "script_location", str(service_directory / "migrations")
    )
    revisions = list(ScriptDirectory.from_config(configuration).walk_revisions())
    heads = [revision.revision for revision in revisions if revision.is_head]
    bases = [revision.revision for revision in revisions if revision.is_base]

    if len(heads) != 1:
        raise RuntimeError("Order migrations must have exactly one head revision.")
    if len(bases) != 1:
        raise RuntimeError("Order migrations must have exactly one base revision.")
    if len({revision.revision for revision in revisions}) != len(revisions):
        raise RuntimeError("Order migrations contain duplicate revision identifiers.")

    report = {
        "status": "passed",
        "service": "order-service",
        "revision_count": len(revisions),
        "base_revision": bases[0],
        "head_revision": heads[0],
        "revisions": [revision.revision for revision in reversed(revisions)],
        "validation": "single connected Alembic revision graph",
    }
    arguments.report.parent.mkdir(parents=True, exist_ok=True)
    arguments.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        "Order migration integrity passed: "
        f"{len(revisions)} revisions, base={bases[0]}, head={heads[0]}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
