#!/usr/bin/env python3
"""Generate registry/index.json from two sources.

  1. Internal skills  — the plugins declared in .claude-plugin/marketplace.json
                        (this repo's own skill packages).
  2. Community skills — submission folders under registry/skills/<author>__<name>/
                        each containing a metadata.json (validated by validate.py).

Usage:
    python registry/scripts/build_index.py            # deterministic, no network
    python registry/scripts/build_index.py --github   # enrich entries with live
                                                       # GitHub stars/forks (network)
    python registry/scripts/build_index.py --check     # fail if index.json is stale

The default run performs no network calls so the committed index.json is
reproducible in CI. Stdlib only.

Exit code: 0 on success; with --check, 1 if the on-disk index.json differs from
a freshly built one.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

REGISTRY_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = REGISTRY_ROOT.parent
MARKETPLACE_PATH = REPO_ROOT / ".claude-plugin" / "marketplace.json"
SKILLS_DIR = REGISTRY_ROOT / "skills"
INDEX_PATH = REGISTRY_ROOT / "index.json"

REPO_URL = "https://github.com/alirezarezvani/claude-skills"
RAW_BASE = "https://raw.githubusercontent.com/alirezarezvani/claude-skills/main"
TREE_BASE = f"{REPO_URL}/tree/main"


def _git_first_commit_date(rel_path: str) -> str:
    """Date of the first commit that touched rel_path (YYYY-MM-DD)."""
    try:
        out = subprocess.run(
            ["git", "log", "--diff-filter=A", "--format=%aI", "--", rel_path],
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=20,
        ).stdout.strip().splitlines()
        if out:
            return out[-1].split("T")[0]
    except (subprocess.SubprocessError, OSError):
        pass
    return date.today().isoformat()


def _fetch_github_stats(repository: str) -> dict | None:
    """Best-effort GitHub repo stats via the public API (only with --github)."""
    import urllib.error
    import urllib.request

    repo_path = repository.replace("https://github.com/", "").rstrip("/")
    api = f"https://api.github.com/repos/{repo_path}"
    try:
        req = urllib.request.Request(api, headers={"User-Agent": "claude-skills-registry"})
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310 (https only)
            data = json.loads(resp.read().decode("utf-8"))
        return {
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "issues": data.get("open_issues_count", 0),
            "language": data.get("language"),
            "avatar": (data.get("owner") or {}).get("avatar_url", ""),
            "description": data.get("description"),
        }
    except (urllib.error.URLError, ValueError, KeyError, TimeoutError):
        return None


def _entry_base(meta: dict) -> dict:
    """Common fields shared by internal and community entries."""
    return {
        "name": meta["name"],
        "author": meta["author"],
        "description": meta["description"],
        "category": meta.get("category", "other"),
        "tags": meta.get("tags", []),
        "version": meta.get("version", "0.0.0"),
        "license": meta.get("license", "MIT"),
    }


def build_internal_entries(with_github: bool) -> list[dict]:
    if not MARKETPLACE_PATH.exists():
        return []
    market = json.loads(MARKETPLACE_PATH.read_text(encoding="utf-8"))
    owner = (market.get("owner") or {}).get("name", "alirezarezvani")
    entries: list[dict] = []
    for plugin in market.get("plugins", []):
        source = (plugin.get("source") or "").lstrip("./")
        author = (plugin.get("author") or {}).get("name") or owner
        skill_md = REPO_ROOT / source / "SKILL.md"
        readme = (
            f"{RAW_BASE}/{source}/SKILL.md"
            if skill_md.exists()
            else f"{TREE_BASE}/{source}"
        )
        entry = {
            "name": plugin["name"],
            "author": author,
            "description": plugin.get("description", ""),
            "category": plugin.get("category", "other"),
            "tags": plugin.get("keywords", []),
            "version": plugin.get("version", "0.0.0"),
            "license": "MIT",
            "origin": "internal",
            "repository": REPO_URL,
            "path": source,
            "readme": readme,
            "icon": None,
            "banner": None,
            "github": None,
            "added_at": _git_first_commit_date(source) if source else date.today().isoformat(),
        }
        if with_github:
            entry["github"] = _fetch_github_stats(REPO_URL)
        entries.append(entry)
    return entries


def build_community_entries(with_github: bool) -> list[dict]:
    if not SKILLS_DIR.exists():
        return []
    entries: list[dict] = []
    for folder in sorted(SKILLS_DIR.iterdir()):
        if not folder.is_dir() or "__" not in folder.name:
            continue
        meta_path = folder / "metadata.json"
        if not meta_path.exists():
            print(f"  skipping {folder.name}: no metadata.json", file=sys.stderr)
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"  skipping {folder.name}: invalid metadata.json — {exc}", file=sys.stderr)
            continue

        has_icon = meta.get("icon") is True and (folder / "icon.png").exists()
        has_banner = meta.get("banner") is True and (folder / "banner.png").exists()
        rel = f"registry/skills/{folder.name}"

        entry = _entry_base(meta)
        entry.update(
            {
                "origin": "community",
                "repository": meta["repository"],
                "path": meta.get("path", ""),
                "readme": f"{RAW_BASE}/{rel}/README.md",
                "icon": f"{RAW_BASE}/{rel}/icon.png" if has_icon else None,
                "banner": f"{RAW_BASE}/{rel}/banner.png" if has_banner else None,
                "github": _fetch_github_stats(meta["repository"]) if with_github else None,
                "added_at": _git_first_commit_date(rel),
            }
        )
        if "adapters" in meta:
            entry["adapters"] = meta["adapters"]
        if "model" in meta:
            entry["model"] = meta["model"]
        entries.append(entry)
    return entries


def build_index(with_github: bool = False) -> dict:
    internal = build_internal_entries(with_github)
    community = build_community_entries(with_github)
    agents = internal + community
    agents.sort(key=lambda e: (e["origin"] != "community", e["name"].lower()))
    return {
        "skills": agents,
        "total": len(agents),
        "counts": {"internal": len(internal), "community": len(community)},
        "generated_at": date.today().isoformat(),
    }


def _serialize(index: dict) -> str:
    return json.dumps(index, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build registry/index.json.")
    parser.add_argument(
        "--github", action="store_true", help="enrich entries with live GitHub stats (network)"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="do not write; exit 1 if index.json is out of date",
    )
    args = parser.parse_args(argv)

    index = build_index(with_github=args.github)
    serialized = _serialize(index)

    if args.check:
        # generated_at changes daily; compare everything except that field.
        current = json.loads(INDEX_PATH.read_text(encoding="utf-8")) if INDEX_PATH.exists() else {}
        fresh = json.loads(serialized)
        current.pop("generated_at", None)
        fresh.pop("generated_at", None)
        if current != fresh:
            print(
                "index.json is stale. Run: python registry/scripts/build_index.py",
                file=sys.stderr,
            )
            return 1
        print("index.json is up to date.")
        return 0

    INDEX_PATH.write_text(serialized, encoding="utf-8")
    print(
        f"Wrote {INDEX_PATH.relative_to(REPO_ROOT)}: "
        f"{index['total']} skills "
        f"({index['counts']['internal']} internal, {index['counts']['community']} community)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
