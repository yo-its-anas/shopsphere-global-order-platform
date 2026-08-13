#!/usr/bin/env python3
"""Write a minimal JUnit result for a separately executed validation command."""

from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--suite", required=True)
    parser.add_argument("--test", required=True)
    parser.add_argument("--status", required=True, choices=("passed", "failed"))
    parser.add_argument("--message", required=True)
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    failures = "1" if arguments.status == "failed" else "0"
    suite = ET.Element(
        "testsuite", name=arguments.suite, tests="1", failures=failures, skipped="0"
    )
    case = ET.SubElement(suite, "testcase", classname=arguments.suite, name=arguments.test)
    if arguments.status == "failed":
        ET.SubElement(case, "failure", message=arguments.message)
    ET.SubElement(case, "system-out").text = arguments.message
    arguments.report.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(suite).write(arguments.report, encoding="utf-8", xml_declaration=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
