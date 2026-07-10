#!/usr/bin/env python3
"""Validate distillate category counts before publishing generated artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


class ValidationError(RuntimeError):
    pass


def indexed_counts(summary: dict[str, Any]) -> dict[str, dict[str, int]]:
    indexed: dict[str, dict[str, int]] = {}
    for section in ("published_categories", "aggregates"):
        items = summary.get(section, [])
        if not isinstance(items, list):
            raise ValidationError(f"Summary field {section} must be an array")
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("name"), str):
                raise ValidationError(f"Invalid category entry in {section}")
            counts: dict[str, int] = {}
            for field in ("domains", "ip_cidrs"):
                value = item.get(field, 0)
                if not isinstance(value, int) or value < 0:
                    raise ValidationError(f"Invalid {field} count for {item['name']}")
                counts[field] = value
            indexed[item["name"]] = counts
    return indexed


def validate_summary_delta(
    previous: dict[str, Any],
    current: dict[str, Any],
    *,
    allow_large_diff: bool = False,
) -> None:
    previous_counts = indexed_counts(previous)
    current_counts = indexed_counts(current)

    for name, old_counts in previous_counts.items():
        if name not in current_counts:
            raise ValidationError(f"Required category is missing: {name}")
        for field, old_value in old_counts.items():
            new_value = current_counts[name][field]
            if old_value > 0 and new_value == 0:
                raise ValidationError(f"Required category became empty: {name}.{field}")
            if allow_large_diff or old_value == 0:
                continue
            if new_value * 100 < old_value * 60:
                raise ValidationError(f"Category count dropped by more than 40%: {name}.{field}")
            if new_value > old_value * 2:
                raise ValidationError(f"Category count grew by more than 100%: {name}.{field}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previous", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--allow-large-diff", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    previous = json.loads(args.previous.read_text(encoding="utf-8"))
    current = json.loads(args.current.read_text(encoding="utf-8"))
    validate_summary_delta(previous, current, allow_large_diff=args.allow_large_diff)
    print("Distillate summary validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
