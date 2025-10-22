"""Utilities for synchronising Accountability Buddy data with an Obsidian vault."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


def parse_goals_from_vapi_output(structured_output: Optional[dict]) -> List[str]:
    """Extract a list of goal strings from a Vapi structured output payload.

    Expected Vapi structured outputs typically follow one of two patterns:
    1. A dictionary containing a `result` field with a numbered list rendered
       as plain text (e.g., ``"1. Finish report\n2. Workout"``).
    2. A dictionary containing a list of goal strings (e.g.,
       ``{"goals": ["Finish report", "Workout"]}``).

    The function attempts to normalise both forms into a flat ``List[str]``.
    If the payload is missing or cannot be parsed, an empty list is returned.
    """
    if not structured_output:
        return []

    goals: List[str] = []

    def _clean_goal(line: str) -> str:
        stripped = line.strip()
        if not stripped:
            return ""
        # Remove common numbering prefixes like "1." or "1)".
        if stripped[0].isdigit():
            parts = stripped.split(maxsplit=1)
            if len(parts) == 2 and parts[0].rstrip(").").isdigit():
                return parts[1].strip()
        # Remove checkbox prefix if present.
        if stripped.lower().startswith("[ ]") or stripped.lower().startswith("[x]"):
            return stripped[3:].strip()
        return stripped

    for value in structured_output.values():
        if isinstance(value, dict):
            # Nested dictionary – recurse one level.
            nested_goals = parse_goals_from_vapi_output(value)
            goals.extend(nested_goals)
            continue

        if isinstance(value, list):
            goals.extend([_clean_goal(str(item)) for item in value if str(item).strip()])
            continue

        if isinstance(value, str):
            lines = value.splitlines()
            cleaned = [_clean_goal(line) for line in lines]
            goals.extend([line for line in cleaned if line])

    # Deduplicate while preserving order.
    seen = set()
    unique_goals: List[str] = []
    for goal in goals:
        if goal not in seen:
            unique_goals.append(goal)
            seen.add(goal)
    return unique_goals


class ObsidianGitSync:
    """Clone, update, and push an Obsidian vault hosted on GitHub."""

    def __init__(
        self,
        repo_url: str,
        github_token: str,
        git_user_name: Optional[str] = None,
        git_user_email: Optional[str] = None,
    ) -> None:
        self.repo_url = repo_url
        self.github_token = github_token
        self.git_user_name = git_user_name or os.environ.get(
            "OBSIDIAN_GIT_USER_NAME", "Accountability Buddy Bot"
        )
        self.git_user_email = git_user_email or os.environ.get(
            "OBSIDIAN_GIT_USER_EMAIL", "bot@accountability.local"
        )
        self.temp_dir = Path(tempfile.mkdtemp(prefix="obsidian_vault_"))
        self.repo_dir: Optional[Path] = None

    @property
    def vault_path(self) -> Path:
        if not self.repo_dir:
            raise RuntimeError("Repository has not been cloned yet.")
        return self.repo_dir

    def __enter__(self) -> "ObsidianGitSync":
        self.clone_repo()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.cleanup()

    # Git operations -----------------------------------------------------

    def clone_repo(self) -> None:
        """Clone the Obsidian vault using a fresh temporary directory."""
        if self.repo_dir and self.repo_dir.exists():
            return

        repo_name = self._repo_name(self.repo_url)
        target_dir = self.temp_dir / repo_name

        auth_url = self._build_authenticated_url(self.repo_url, self.github_token)
        print(f"[ObsidianGitSync] Cloning vault into {target_dir}")
        self._run_git(["clone", auth_url, str(target_dir)])

        self.repo_dir = target_dir
        self._configure_git_identity()

    def commit_and_push(self, message: str) -> bool:
        """Commit staged changes and push to the remote repository.

        Returns ``True`` if a commit was created and pushed, otherwise ``False``.
        """
        if not self.repo_dir:
            raise RuntimeError("Cannot commit before repository clone.")

        status = self._run_git(["status", "--porcelain"], capture_output=True).strip()
        if not status:
            print("[ObsidianGitSync] No changes detected; skipping commit.")
            return False

        print(f"[ObsidianGitSync] Committing changes: {message}")
        self._run_git(["add", "."], check=True)
        self._run_git(["commit", "-m", message], check=True)
        self._run_git(["push", "origin", "HEAD"], check=True)
        return True

    def cleanup(self) -> None:
        """Remove the temporary directory used for cloning."""
        if self.temp_dir.exists():
            print(f"[ObsidianGitSync] Cleaning up {self.temp_dir}")
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _configure_git_identity(self) -> None:
        """Set the git author identity for commits created in the vault."""
        if not self.repo_dir:
            return
        self._run_git(["config", "user.name", self.git_user_name])
        self._run_git(["config", "user.email", self.git_user_email])

    def _run_git(
        self,
        args: Iterable[str],
        check: bool = True,
        capture_output: bool = False,
    ) -> str:
        """Execute a git command inside the cloned repository."""
        cmd = ["git"]
        cmd.extend(args)
        print(f"[ObsidianGitSync] Running: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            cwd=str(self.repo_dir or self.temp_dir),
            check=check,
            capture_output=capture_output,
            text=True,
        )
        if capture_output:
            return result.stdout
        return ""

    @staticmethod
    def _build_authenticated_url(repo_url: str, token: str) -> str:
        """Inject the GitHub token into the repository URL if needed."""
        if token in repo_url:
            return repo_url
        if repo_url.startswith("https://"):
            return repo_url.replace("https://", f"https://{token}@", 1)
        return f"https://{token}@{repo_url}"

    @staticmethod
    def _repo_name(repo_url: str) -> str:
        """Derive the repository directory name from its URL."""
        name = Path(repo_url.rstrip("/")).name
        if name.endswith(".git"):
            name = name[:-4]
        return name


class ObsidianSync:
    """Manage Obsidian vault files for Accountability Buddy."""

    accountability_path = Path("Accountability") / "Daily Logs"
    daily_notes_path = Path("Daily Notes")

    def __init__(self, vault_path: str | Path, git_sync: Optional[ObsidianGitSync] = None) -> None:
        self.vault_path = Path(vault_path)
        self.git_sync = git_sync

    def create_morning_entry(
        self,
        goals: List[str],
        call_time: datetime,
        call_data: Dict[str, str],
    ) -> Path:
        """Create a morning accountability entry for the given date."""
        date_str = call_time.strftime("%Y-%m-%d")
        file_path = self.vault_path / self.accountability_path / f"{date_str}-accountability.md"
        file_path.parent.mkdir(parents=True, exist_ok=True)

        metadata = {
            "date": date_str,
            "morning_time": call_time.isoformat(),
            "morning_call_id": call_data.get("id", ""),
            "morning_call_status": call_data.get("status", ""),
            "evening_time": "",
            "evening_call_id": "",
            "completion_rate": 0,
            "completed_goals": [],
        }

        content = self._render_morning_content(metadata, goals)
        file_path.write_text(content, encoding="utf-8")
        print(f"[ObsidianSync] Morning entry created at {file_path}")

        self._update_daily_note(date_str, call_time)

        if self.git_sync:
            message = f"Morning accountability check-in - {date_str}"
            self.git_sync.commit_and_push(message)

        return file_path

    def update_evening_entry(
        self,
        goals: List[str],
        completed: List[bool],
        call_time: datetime,
        reflections: str = "",
    ) -> Optional[Path]:
        """Update the daily accountability entry with evening results."""
        if not goals:
            print("[ObsidianSync] No goals provided for evening update; skipping.")
            return None

        date_str = call_time.strftime("%Y-%m-%d")
        file_path = self.vault_path / self.accountability_path / f"{date_str}-accountability.md"
        if not file_path.exists():
            print(f"[ObsidianSync] Morning entry {file_path} not found; cannot update evening review.")
            return None

        metadata, _ = self._read_accountability_file(file_path)
        metadata["evening_time"] = call_time.isoformat()
        metadata["completed_goals"] = [goal for goal, done in zip(goals, completed) if done]

        total = len(goals)
        completed_count = sum(1 for done in completed if done)
        completion_rate = int((completed_count / total) * 100) if total else 0
        metadata["completion_rate"] = completion_rate

        content = self._render_evening_content(metadata, goals, completed, reflections)
        file_path.write_text(content, encoding="utf-8")
        print(f"[ObsidianSync] Evening entry updated at {file_path}")

        if self.git_sync:
            message = f"Evening accountability review - {date_str} ({completion_rate}% complete)"
            self.git_sync.commit_and_push(message)

        return file_path

    # Internal helpers ---------------------------------------------------

    def _render_morning_content(self, metadata: Dict[str, object], goals: List[str]) -> str:
        """Render the morning accountability Markdown content."""
        frontmatter = self._format_frontmatter(metadata)
        goals_section = self._format_goals(goals, completed=[])

        body = [
            frontmatter,
            "# Morning Accountability",
            "",
            "## Goals",
            goals_section,
            "",
            "## Evening Review 🌙",
            "Evening Review 🌙 - *Pending...*",
            "",
        ]
        return "\n".join(body).strip() + "\n"

    def _render_evening_content(
        self,
        metadata: Dict[str, object],
        goals: List[str],
        completed: List[bool],
        reflections: str,
    ) -> str:
        """Render the evening accountability Markdown update."""
        frontmatter = self._format_frontmatter(metadata)
        goals_section = self._format_goals(goals, completed)

        completed_goals = [goal for goal, done in zip(goals, completed) if done]
        incomplete_goals = [goal for goal, done in zip(goals, completed) if not done]

        body = [
            frontmatter,
            "# Morning Accountability",
            "",
            "## Goals",
            goals_section,
            "",
            "## Evening Review 🌙",
            f"- Completion Rate: {metadata.get('completion_rate', 0)}%",
        ]

        if completed_goals:
            body.append("- Completed:")
            body.extend([f"  - ✅ {goal}" for goal in completed_goals])
        if incomplete_goals:
            body.append("- Not Completed:")
            body.extend([f"  - ⚪️ {goal}" for goal in incomplete_goals])

        if reflections:
            body.append("")
            body.append("### Reflections")
            body.append(reflections.strip())

        body.append("")
        return "\n".join(body).strip() + "\n"

    def _format_frontmatter(self, metadata: Dict[str, object]) -> str:
        """Convert the metadata dictionary into YAML frontmatter."""
        lines = ["---"]
        for key, value in metadata.items():
            lines.append(f"{key}: {json.dumps(value)}")
        lines.append("---")
        return "\n".join(lines)

    def _format_goals(self, goals: List[str], completed: Iterable[bool]) -> str:
        """Render the numbered goal list with checkbox state."""
        completed_list = list(completed)
        lines = []
        for index, goal in enumerate(goals, start=1):
            is_completed = completed_list[index - 1] if index - 1 < len(completed_list) else False
            checkbox = "[x]" if is_completed else "[ ]"
            lines.append(f"{index}. {checkbox} {goal}")
        return "\n".join(lines) if lines else "No goals recorded."

    def _read_accountability_file(self, path: Path) -> Tuple[Dict[str, object], str]:
        """Read an existing accountability file and return metadata and body."""
        content = path.read_text(encoding="utf-8")
        if not content.startswith("---"):
            return {}, content

        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}, content

        frontmatter_text = parts[1].strip()
        metadata: Dict[str, object] = {}
        for line in frontmatter_text.splitlines():
            if ":" not in line:
                continue
            key, raw_value = line.split(":", 1)
            key = key.strip()
            raw_value = raw_value.strip()
            try:
                metadata[key] = json.loads(raw_value)
            except json.JSONDecodeError:
                metadata[key] = raw_value

        return metadata, parts[2]

    def _update_daily_note(self, date_str: str, call_time: datetime) -> Path:
        """Ensure the daily note embeds the accountability log for the given date."""
        note_path = self.vault_path / self.daily_notes_path / f"{date_str}.md"
        note_path.parent.mkdir(parents=True, exist_ok=True)
        embed = f"![[{date_str}-accountability]]"

        if note_path.exists():
            content = note_path.read_text(encoding="utf-8")
            if embed in content:
                return note_path
            lines = content.splitlines()

            # Try to insert under an existing "## Accountability" header.
            for index, line in enumerate(lines):
                if line.strip().lower() == "## accountability":
                    insertion_index = index + 1
                    lines.insert(insertion_index, "")
                    lines.insert(insertion_index + 1, embed)
                    note_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                    print(f"[ObsidianSync] Daily note updated at {note_path}")
                    return note_path

            # Fallback: append a new section at the end.
            lines.extend(["", "## Accountability", embed])
            note_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            print(f"[ObsidianSync] Daily note updated at {note_path}")
            return note_path

        # Create a new daily note.
        title = call_time.strftime("%A, %B %d, %Y")
        content = [
            f"# {title}",
            "",
            "## Accountability",
            embed,
            "",
        ]
        note_path.write_text("\n".join(content), encoding="utf-8")
        print(f"[ObsidianSync] Daily note created at {note_path}")
        return note_path


__all__ = [
    "ObsidianGitSync",
    "ObsidianSync",
    "parse_goals_from_vapi_output",
]
