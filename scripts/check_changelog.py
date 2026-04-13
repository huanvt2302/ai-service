#!/usr/bin/env python3
"""
Changelog Enforcement Script
=============================
Verifies that any staged change to tracked paths has a corresponding
changelog entry file in docs/changelog/ dated today.

Structure enforced:
  docs/changelog/YYYY-MM-DD_task_info.md

Usage:
    python scripts/check_changelog.py

Exit codes:
    0 — changelog is up to date
    1 — changelog update required (BLOCKS commit)

Install as pre-commit hook:
    cp scripts/check_changelog.py .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit
"""

import subprocess
import sys
import re
from datetime import date
from pathlib import Path

# Paths that REQUIRE a changelog entry when modified
TRACKED_PATHS = [
    "backend/routes/",
    "backend/models.py",
    "backend/alembic/",
    "backend/serve/",
    "backend/workers/",
    "frontend/app/",
    "frontend/lib/api.ts",
    "docker-compose.yml",
    "monitoring/",
]

CHANGELOG_DIR = Path("docs/changelog")
CHANGELOG_INDEX = Path("docs/changelog.md")
TODAY = date.today().isoformat()  # e.g. "2026-04-10"


def get_staged_files() -> list[str]:
    """Return list of staged file paths."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMRD"],
        capture_output=True, text=True
    )
    return result.stdout.strip().splitlines()


def is_tracked(filepath: str) -> bool:
    """Return True if the filepath falls under a tracked path."""
    for tracked in TRACKED_PATHS:
        if filepath.startswith(tracked):
            return True
    return False


def get_todays_changelog_files(staged: list[str]) -> list[str]:
    """Return staged changelog files matching today's date pattern."""
    pattern = re.compile(rf"^docs/changelog/{TODAY}_.+\.md$")
    return [f for f in staged if pattern.match(f)]


def changelog_dir_has_today() -> bool:
    """Return True if docs/changelog/ already has a file with today's date (committed)."""
    if not CHANGELOG_DIR.exists():
        return False
    pattern = re.compile(rf"^{TODAY}_.+\.md$")
    return any(pattern.match(f.name) for f in CHANGELOG_DIR.iterdir() if f.is_file())


def main():
    staged = get_staged_files()

    # Find tracked files being modified
    tracked_changes = [f for f in staged if is_tracked(f)]

    if not tracked_changes:
        print("✅ No tracked paths modified — changelog check skipped.")
        sys.exit(0)

    print(f"📝 Tracked files being committed:")
    for f in tracked_changes:
        print(f"   {f}")

    # Check if a new changelog file for today is staged
    todays_entries = get_todays_changelog_files(staged)

    if todays_entries:
        print(f"\n✅ Changelog file staged:")
        for f in todays_entries:
            print(f"   {f}")
        sys.exit(0)

    # Check if a today's file already exists (committed in a previous commit today)
    if changelog_dir_has_today():
        print(f"\n✅ Today's changelog file already exists in docs/changelog/ — OK.")
        sys.exit(0)

    # BLOCKED
    print(f"\n❌ BLOCKED: You modified tracked paths but did not create a changelog file.")
    print(f"\n   Required: Create a new file matching:")
    print(f"   docs/changelog/{TODAY}_your_task_name.md")
    print(f"\n   File template:")
    print(f"   # {TODAY} — Task Title")
    print(f"   **Type:** Feature | Fix | Docs | Refactor | Security")
    print(f"   ## Added / Changed / Fixed / Removed")
    print(f"   * Your change description")
    print(f"\n   Then stage it: git add docs/changelog/{TODAY}_your_task_name.md")
    print(f"   Also update the index: git add docs/changelog.md")
    sys.exit(1)


if __name__ == "__main__":
    main()
