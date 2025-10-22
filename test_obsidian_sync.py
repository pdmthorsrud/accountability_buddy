"""Utility script to verify Obsidian vault updates for Accountability Buddy.

Run this script manually to make sure the Obsidian integration can clone the
vault, write morning and evening entries, and push the resulting commit.

Usage:
    export OBSIDIAN_REPO_URL="https://github.com/..."
    export OBSIDIAN_GITHUB_TOKEN="ghp_..."
    # Optionally override git author identity:
    # export OBSIDIAN_GIT_USER_NAME="Accountability Buddy Bot"
    # export OBSIDIAN_GIT_USER_EMAIL="bot@accountability.local"
    python test_obsidian_sync.py
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import List

from obsidian_git_sync import ObsidianGitSync, ObsidianSync


def _require_env(var_name: str) -> str:
    """Fetch an environment variable or exit with an informative error."""
    value = os.environ.get(var_name)
    if not value:
        print(f"Missing required environment variable: {var_name}", file=sys.stderr)
        sys.exit(1)
    return value


def _sample_goals() -> List[str]:
    """Return sample goals for test entries."""
    return [
        "Draft test summary for Obsidian sync",
        "Review Git history for automated entries",
        "Plan improvements for accountability workflow",
    ]


def main() -> None:
    repo_url = _require_env("OBSIDIAN_REPO_URL")
    github_token = _require_env("OBSIDIAN_GITHUB_TOKEN")
    git_user_name = os.environ.get("OBSIDIAN_GIT_USER_NAME")
    git_user_email = os.environ.get("OBSIDIAN_GIT_USER_EMAIL")

    # Allow overriding the date for testing to avoid clashing with real entries.
    date_override = os.environ.get("OBSIDIAN_TEST_DATE")
    if date_override:
        try:
            call_time = datetime.fromisoformat(date_override)
        except ValueError:
            print("OBSIDIAN_TEST_DATE must be ISO-8601 (e.g., 2025-02-05T08:00:00)", file=sys.stderr)
            sys.exit(1)
    else:
        call_time = datetime.now()

    goals = _sample_goals()
    call_data = {
        "id": f"test-morning-{call_time.strftime('%Y%m%d%H%M%S')}",
        "status": "ended",
    }

    completed = [True, False, True]
    reflections = (
        "Test run using test_obsidian_sync.py to confirm Git-based Obsidian updates. "
        "Review the commit history on GitHub to verify both morning and evening entries."
    )

    print("Starting Obsidian sync test...")
    with ObsidianGitSync(
        repo_url=repo_url,
        github_token=github_token,
        git_user_name=git_user_name,
        git_user_email=git_user_email,
    ) as git_sync:
        obsidian = ObsidianSync(str(git_sync.vault_path), git_sync=git_sync)

        morning_path = obsidian.create_morning_entry(goals, call_time, call_data)
        print(f"Morning entry written to: {morning_path}")

        evening_path = obsidian.update_evening_entry(goals, completed, call_time, reflections)
        if evening_path:
            print(f"Evening entry updated at: {evening_path}")
        else:
            print("Evening entry was not updated (morning file missing?).")

    print("Obsidian sync test complete. Check the repository for new commits.")


if __name__ == "__main__":
    main()
