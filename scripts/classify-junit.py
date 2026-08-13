#!/usr/bin/env python3
"""Write an explicit passed, failed, or skipped/not applicable JUnit classification."""

from __future__ import annotations

import argparse
from pathlib import Path
from xml.etree import ElementTree


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--status-file", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    root = ElementTree.parse(arguments.report).getroot()  # noqa: S314
    cases = list(root.iter("testcase"))
    failures = sum(
        any(child.tag in {"failure", "error"} for child in case) for case in cases
    )
    skipped = sum(any(child.tag == "skipped" for child in case) for case in cases)
    passed = len(cases) - failures - skipped

    if failures:
        status = "failed"
    elif cases and skipped == len(cases):
        status = "skipped/not applicable"
    elif cases:
        status = "passed"
    else:
        status = "failed"

    reason = f"passed={passed}, failed={failures}, skipped/not applicable={skipped}"
    arguments.status_file.parent.mkdir(parents=True, exist_ok=True)
    arguments.status_file.write_text(
        f"status={status}\nreason={reason}\n", encoding="utf-8"
    )
    print(f"JUnit classification: {status} ({reason})")
    return 1 if status == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
