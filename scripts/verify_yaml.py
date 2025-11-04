#!/usr/bin/env python3
"""
verify_yaml.py

Lightweight verification for generated AAP 2.5 CaC YAML under ./_cac_25.

What this does:
  1. Validates each expected YAML file exists.
  2. Parses YAML.
  3. Performs minimal schema checks on list items.

Usage:
  python3 scripts/verify_yaml.py
  python3 scripts/verify_yaml.py --path ./_cac_25 --strict

Exit codes:
  0 - All checks passed
  1 - Soft warnings encountered
  2 - Errors encountered
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

DEFAULT_DIR = Path("./_cac_25")

EXPECTED_FILES: Dict[str, str] = {
    "controller_organizations.yml": "controller_organizations",
    "controller_credentials.yml": "controller_credentials",
    "controller_projects.yml": "controller_projects",
    "controller_inventories.yml": "controller_inventories",
    "controller_templates.yml": "controller_templates",
    "controller_workflows.yml": "controller_workflows",
    "controller_execution_environments.yml": "controller_execution_environments",
}

REQUIRED_FIELDS_PER_LIST_ITEM: Dict[str, List[str]] = {
    # Minimal fields per object set below as we have no access. These will likely need to be extended.
    "controller_organizations": ["name"],
    "controller_credentials": ["name", "credential_type"],
    "controller_projects": ["name"],
    "controller_inventories": ["name"],
    "controller_templates": ["name", "project", "job_type"],
    "controller_workflows": ["name"],
    "controller_execution_environments": ["name", "image"],
}


def load_yaml(path: Path) -> Dict[str, Any]:
    """Load a YAML file into a Python object."""
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def validate_top_level(data: Dict[str, Any], expected_key: str) -> Tuple[bool, str]:
    """Verify the YAML contains the expected top-level key with a list value."""
    if expected_key not in data:
        return False, f"Missing top-level key '{expected_key}'."
    if not isinstance(data[expected_key], list):
        return False, f"Top-level key '{expected_key}' must be a list."
    return True, ""


def validate_list_items(kind: str, items: List[Dict[str, Any]]) -> List[str]:
    """
    Perform schema checks on list items for a given kind. These are minimal and should be extended as needed.

    Ensures presence of required fields and basic types.
    """
    errors: List[str] = []
    required = REQUIRED_FIELDS_PER_LIST_ITEM.get(kind, ["name"])

    for idx, obj in enumerate(items):
        if not isinstance(obj, dict):
            errors.append(f"[{kind}][{idx}] must be a mapping dict.")
            continue
        for field in required:
            if field not in obj or obj[field] in (None, ""):
                errors.append(f"[{kind}][{idx}] missing required field '{field}'.")
        if "state" in obj and not isinstance(obj["state"], str):
            errors.append(f"[{kind}][{idx}] field 'state' must be a string if present.")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify CaC YAML under _cac_25.")
    parser.add_argument("--path", type=Path, default=DEFAULT_DIR, help="Directory containing YAML files.")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors.")
    args = parser.parse_args()

    base: Path = args.path
    if not base.exists():
        print(f"ERROR: Path not found: {base}", file=sys.stderr)
        return 2

    warnings: List[str] = []
    errors: List[str] = []

    for fname, topkey in EXPECTED_FILES.items():
        fpath = base / fname
        if not fpath.exists():
            warnings.append(f"Missing expected file: {fpath}")
            continue

        try:
            data = load_yaml(fpath)
        except Exception as e:
            errors.append(f"Failed to parse YAML: {fpath} :: {e}")
            continue

        ok, msg = validate_top_level(data, topkey)
        if not ok:
            errors.append(f"{fpath}: {msg}")
            continue

        items = data.get(topkey, [])
        item_errors = validate_list_items(topkey, items)
        errors.extend([f"{fpath}: {e}" for e in item_errors])

    if errors:
        print("ERRORS:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 2

    if warnings:
        print("WARNINGS:")
        for w in warnings:
            print(f"  - {w}")
        return 1 if args.strict else 0

    print("OK: YAML verification passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())