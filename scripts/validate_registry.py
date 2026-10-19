#!/usr/bin/env python3
"""Validate registry.json (standard library only).

The rules mirror the client in YSocial (``y_web/src/external_runtime/catalog.py``):
an entry accepted here is accepted by YSocial. Run it before opening a pull
request::

    python scripts/validate_registry.py                 # structure and rules
    python scripts/validate_registry.py --check-repos   # + the repositories exist

``--check-repos`` queries the GitHub API (set ``GITHUB_TOKEN`` to avoid rate limits).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

SCHEMA_VERSION = 1
OFFICIAL_OWNERS = {"ysocialtwin"}
RECIPES = {"auto", "requirements", "pip-editable"}
CATEGORIES = {"agent_extensions", "frontend_extensions", "backend_extensions"}
TRUST = {"official", "community"}
# keys and directories used by the plugins that ship inside YSocial
BUILTIN_IDS = {
    "microblogging_client",
    "microblogging_server",
    "forum_client",
    "forum_server",
    "photo_sharing",
    "hpc",
    "y_memory_subsystem",
    "reactive_agents",
    "frontend_adds_on",
    "scenario_design",
    "training_modules",
}
KNOWN_FIELDS = {
    "id", "name", "description", "category", "repo", "branch", "directory",
    "recipe", "trust", "min_ysocial_version", "authors", "import_name", "private",
}  # fmt: skip

ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,47}$")
REPO_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})/[A-Za-z0-9._-]{1,100}$")
BRANCH_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,99}$")
DIR_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
MODULE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$")
VERSION_RE = re.compile(r"^\d+(\.\d+){0,3}$")


def validate(payload) -> list[str]:
    """Return the list of problems (empty = valid)."""
    if not isinstance(payload, dict):
        return ["the file must contain a JSON object"]
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    plugins = payload.get("plugins")
    if not isinstance(plugins, list):
        return errors + ["'plugins' must be a list"]
    if len(plugins) > 500:
        errors.append("at most 500 plugins")

    ids: set[str] = set()
    repos: set[str] = set()
    dirs: set[str] = set()
    for i, entry in enumerate(plugins):
        where = f"plugins[{i}]"
        if not isinstance(entry, dict):
            errors.append(f"{where}: must be an object")
            continue
        pid = entry.get("id")
        where = f"plugins[{i}] ({pid})"
        for extra in sorted(set(entry) - KNOWN_FIELDS):
            errors.append(f"{where}: unknown field {extra!r}")
        if not isinstance(pid, str) or not ID_RE.match(pid):
            errors.append(f"{where}: id must match {ID_RE.pattern}")
        elif pid in BUILTIN_IDS or pid in ids:
            errors.append(f"{where}: id already in use")
        else:
            ids.add(pid)
        if not str(entry.get("name") or "").strip():
            errors.append(f"{where}: name is required")
        elif len(entry["name"]) > 80:
            errors.append(f"{where}: name is longer than 80 characters")
        if len(str(entry.get("description") or "")) > 400:
            errors.append(f"{where}: description is longer than 400 characters")
        if entry.get("category") not in CATEGORIES:
            errors.append(f"{where}: category must be one of {sorted(CATEGORIES)}")
        repo = entry.get("repo")
        if not isinstance(repo, str) or not REPO_RE.match(repo):
            errors.append(f"{where}: repo must look like 'owner/name'")
        else:
            if repo.lower() in repos:
                errors.append(f"{where}: repository listed twice")
            repos.add(repo.lower())
            directory = entry.get("directory") or repo.split("/", 1)[1]
            if not isinstance(directory, str) or not DIR_RE.match(directory):
                errors.append(f"{where}: invalid directory")
            elif directory in {".", ".."} or directory.lower() in dirs:
                errors.append(f"{where}: directory already in use")
            else:
                dirs.add(directory.lower())
            if entry.get("trust") == "official" and (
                repo.split("/", 1)[0].lower() not in OFFICIAL_OWNERS
            ):
                errors.append(
                    f"{where}: trust 'official' is reserved to "
                    f"{sorted(OFFICIAL_OWNERS)} repositories"
                )
        branch = entry.get("branch", "main")
        if not isinstance(branch, str) or not BRANCH_RE.match(branch) or ".." in branch:
            errors.append(f"{where}: invalid branch")
        if entry.get("recipe", "auto") not in RECIPES:
            errors.append(f"{where}: recipe must be one of {sorted(RECIPES)}")
        if entry.get("trust", "community") not in TRUST:
            errors.append(f"{where}: trust must be one of {sorted(TRUST)}")
        version = entry.get("min_ysocial_version")
        if version is not None and not (
            isinstance(version, str) and VERSION_RE.match(version)
        ):
            errors.append(f"{where}: min_ysocial_version must look like 4.0.0")
        name = entry.get("import_name")
        if name is not None and not (isinstance(name, str) and MODULE_RE.match(name)):
            errors.append(f"{where}: invalid import_name")
        authors = entry.get("authors", [])
        if not isinstance(authors, list) or len(authors) > 10:
            errors.append(f"{where}: authors must be a list of at most 10 names")
        if entry.get("private") not in (None, True, False):
            errors.append(f"{where}: private must be true or false")
    return errors


def _api(path: str):
    request = urllib.request.Request(
        f"https://api.github.com/{path}",
        headers={"Accept": "application/vnd.github+json"},
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def check_repositories(payload) -> list[str]:
    """Each repository must exist, be public (unless private=true) and ship meta/info.json."""
    errors: list[str] = []
    for entry in payload.get("plugins", []):
        repo, branch = entry["repo"], entry.get("branch", "main")
        where = f"{entry['id']} ({repo})"
        try:
            info = _api(f"repos/{repo}")
        except urllib.error.HTTPError as exc:
            errors.append(f"{where}: repository not reachable (HTTP {exc.code})")
            continue
        except OSError as exc:
            errors.append(f"{where}: could not query GitHub ({exc})")
            continue
        if info.get("private") and not entry.get("private"):
            errors.append(f"{where}: repository is private (set \"private\": true)")
        if info.get("archived"):
            errors.append(f"{where}: repository is archived")
        try:
            _api(f"repos/{repo}/contents/meta/info.json?ref={branch}")
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                errors.append(f"{where}: meta/info.json not found on '{branch}'")
            else:
                errors.append(f"{where}: could not read meta/info.json (HTTP {exc.code})")
        except OSError as exc:
            errors.append(f"{where}: could not query GitHub ({exc})")
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("file", nargs="?", default=None, help="default: registry.json")
    parser.add_argument("--check-repos", action="store_true")
    args = parser.parse_args(argv)
    path = Path(args.file) if args.file else Path(__file__).resolve().parents[1] / "registry.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"ERROR: cannot read {path}: {exc}")
        return 1
    errors = validate(payload)
    if not errors and args.check_repos:
        errors = check_repositories(payload)
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        return 1
    print(f"OK: {len(payload['plugins'])} plugin(s) in {path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
