#!/usr/bin/env python3
"""Validate a claude-skills registry submission folder.

Usage:
    python registry/scripts/validate.py registry/skills/<author>__<skill-name>/ [more...]
    python registry/scripts/validate.py --all          # validate every submission
    python registry/scripts/validate.py --clone <dir>  # also clone repo + verify SKILL.md

Checks:
  1. metadata.json exists and validates against schema/metadata.schema.json
  2. Folder name matches <author>__<name> from metadata
  3. README.md exists and is non-empty
  4. If icon: true, icon.png exists; if banner: true, banner.png exists
  5. With --clone: clones the repository (shallow) and verifies SKILL.md exists
     at the declared path

Stdlib only. The JSON-Schema validation supports the draft-07 subset used by
schema/metadata.schema.json (type/required/properties/additionalProperties/
enum/pattern/min-maxLength/min-maxItems/uniqueItems/items/format:uri).

Exit code: 0 if all submissions pass, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REGISTRY_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REGISTRY_ROOT / "schema" / "metadata.schema.json"
SKILLS_DIR = REGISTRY_ROOT / "skills"


# --------------------------------------------------------------------------- #
# Minimal JSON-Schema (draft-07 subset) validator
# --------------------------------------------------------------------------- #
def _type_ok(value, expected: str) -> bool:
    if expected == "string":
        return isinstance(value, str)
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return True


def validate_schema(instance, schema, path: str = "") -> list[str]:
    """Return a list of human-readable schema violation strings (empty == valid)."""
    errors: list[str] = []
    here = path or "(root)"

    expected_type = schema.get("type")
    if expected_type and not _type_ok(instance, expected_type):
        errors.append(f"{here}: expected type {expected_type}")
        return errors  # further checks assume the type matched

    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{here}: '{instance}' is not one of {schema['enum']}")

    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(f"{here}: shorter than minLength {schema['minLength']}")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append(f"{here}: longer than maxLength {schema['maxLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append(f"{here}: does not match pattern {schema['pattern']}")
        if schema.get("format") == "uri" and not re.match(r"^[a-z][a-z0-9+.\-]*://", instance):
            errors.append(f"{here}: not a valid URI")

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(f"{here}: fewer than minItems {schema['minItems']}")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append(f"{here}: more than maxItems {schema['maxItems']}")
        if schema.get("uniqueItems") and len(instance) != len(
            {json.dumps(i, sort_keys=True) for i in instance}
        ):
            errors.append(f"{here}: items are not unique")
        item_schema = schema.get("items")
        if item_schema:
            for idx, item in enumerate(instance):
                errors.extend(validate_schema(item, item_schema, f"{here}[{idx}]"))

    if isinstance(instance, dict):
        for req in schema.get("required", []):
            if req not in instance:
                errors.append(f"{here}: missing required property '{req}'")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in instance:
                if key not in props:
                    errors.append(f"{here}: additional property '{key}' not allowed")
        for key, subschema in props.items():
            if key in instance:
                errors.extend(validate_schema(instance[key], subschema, f"{here}.{key}"))

    return errors


# --------------------------------------------------------------------------- #
# Submission validation
# --------------------------------------------------------------------------- #
class Result:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def passed(self) -> bool:
        return not self.errors


def validate_submission(folder: Path, schema: dict, clone: bool = False) -> Result:
    result = Result()
    folder = folder.resolve()

    if not folder.is_dir():
        result.errors.append(f"folder does not exist: {folder}")
        return result

    folder_name = folder.name
    if "__" not in folder_name:
        result.errors.append(
            f"folder name must use <author>__<name> format, got: {folder_name}"
        )
        return result

    metadata_path = folder / "metadata.json"
    if not metadata_path.exists():
        result.errors.append("metadata.json not found")
        return result

    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        result.errors.append(f"metadata.json is not valid JSON: {exc}")
        return result

    for err in validate_schema(metadata, schema):
        result.errors.append(f"schema: {err}")

    author = metadata.get("author")
    name = metadata.get("name")
    if author and name:
        expected = f"{author}__{name}"
        if folder_name != expected:
            result.errors.append(
                f"folder name mismatch: expected '{expected}' from metadata, got '{folder_name}'"
            )

    readme_path = folder / "README.md"
    if not readme_path.exists():
        result.errors.append("README.md not found")
    else:
        content = readme_path.read_text(encoding="utf-8").strip()
        if not content:
            result.errors.append("README.md is empty")
        elif len(content) < 50:
            result.warnings.append("README.md is very short — consider adding more detail")

    if metadata.get("icon") is True and not (folder / "icon.png").exists():
        result.errors.append('icon.png not found but metadata has "icon": true')
    if metadata.get("banner") is True and not (folder / "banner.png").exists():
        result.errors.append('banner.png not found but metadata has "banner": true')

    if clone and isinstance(metadata.get("repository"), str) and not result.errors:
        _clone_and_verify(metadata, result)

    return result


def _clone_and_verify(metadata: dict, result: Result) -> None:
    repo = metadata["repository"]
    tmp = Path(tempfile.mkdtemp(prefix="registry-validate-"))
    try:
        print(f"  cloning {repo} ...")
        proc = subprocess.run(
            ["git", "clone", "--depth", "1", repo, str(tmp)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=60,
            text=True,
        )
        if proc.returncode != 0:
            result.errors.append(f"failed to clone repository: {proc.stdout.strip()[:200]}")
            return
        sub = metadata.get("path", "") or ""
        skill_root = (tmp / sub).resolve()
        if not str(skill_root).startswith(str(tmp.resolve())):
            result.errors.append(f"path escapes repository root: {sub!r}")
            return
        if not (skill_root / "SKILL.md").exists():
            suffix = f' at path "{sub}"' if sub else ""
            result.errors.append(f"SKILL.md not found in repository{suffix}")
    except subprocess.TimeoutExpired:
        result.errors.append("timed out cloning repository")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate registry skill submissions.")
    parser.add_argument("folders", nargs="*", help="submission folder(s) to validate")
    parser.add_argument("--all", action="store_true", help="validate every folder under skills/")
    parser.add_argument(
        "--clone",
        action="store_true",
        help="clone each repository and verify SKILL.md exists (network required)",
    )
    args = parser.parse_args(argv)

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    targets: list[Path] = [Path(f) for f in args.folders]
    if args.all:
        targets = sorted(
            p for p in SKILLS_DIR.iterdir() if p.is_dir() and "__" in p.name
        )

    if not targets:
        parser.error("provide one or more folders, or use --all")

    all_passed = True
    for folder in targets:
        print(f"\nValidating: {folder}")
        result = validate_submission(folder, schema, clone=args.clone)
        for err in result.errors:
            print(f"  x {err}")
        for warn in result.warnings:
            print(f"  ! {warn}")
        if result.passed:
            print("  ok valid")
        else:
            all_passed = False

    print()
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
