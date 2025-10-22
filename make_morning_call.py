import os
from datetime import datetime
from typing import Optional

from vapi import Vapi

from obsidian_git_sync import ObsidianGitSync, ObsidianSync, parse_goals_from_vapi_output

# Load environment variables
VAPI_API_TOKEN = os.environ.get("VAPI_API_TOKEN")
MORNING_ASSISTANT_ID = os.environ.get("MORNING_ASSISTANT_ID")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
TARGET_PHONE_NUMBER = os.environ.get("TARGET_PHONE_NUMBER")

# Validate required environment variables
if not all([VAPI_API_TOKEN, MORNING_ASSISTANT_ID, PHONE_NUMBER_ID, TARGET_PHONE_NUMBER]):
    raise ValueError("Missing required environment variables. Please check .env file.")

client = Vapi(token=VAPI_API_TOKEN)

# Create outbound morning call
print("Initiating morning call...")
print("=" * 50)

call = client.calls.create(
    assistant_id=MORNING_ASSISTANT_ID,
    phone_number_id=PHONE_NUMBER_ID,
    customer={"number": TARGET_PHONE_NUMBER},
)

print(f"\nMorning call initiated successfully!")
print(f"Call ID: {call.id}")
print(f"Status: {call.status}")
print(f"Calling: {TARGET_PHONE_NUMBER}")
print(f"Using morning accountability assistant")


def _parse_vapi_datetime(timestamp: Optional[str]) -> Optional[datetime]:
    if not timestamp:
        return None
    value = timestamp.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _find_latest_structured_call() -> Optional[object]:
    calls_list = client.calls.list()
    for entry in calls_list:
        if not hasattr(entry, "customer") or not entry.customer:
            continue
        customer_number = (
            entry.customer.get("number")
            if isinstance(entry.customer, dict)
            else getattr(entry.customer, "number", None)
        )
        if (
            customer_number == TARGET_PHONE_NUMBER
            and getattr(entry, "assistant_id", None) == MORNING_ASSISTANT_ID
            and getattr(entry, "status", None) == "ended"
        ):
            full_call = client.calls.get(id=entry.id)
            artifact = getattr(full_call, "artifact", None)
            structured_outputs = getattr(artifact, "structured_outputs", {}) if artifact else {}
            if structured_outputs:
                return full_call
    return None


def _sync_morning_to_obsidian() -> None:
    obsidian_enabled = os.environ.get("OBSIDIAN_ENABLED", "false").lower() == "true"
    if not obsidian_enabled:
        print("Obsidian sync disabled; skipping vault update.")
        return

    repo_url = os.environ.get("OBSIDIAN_REPO_URL")
    github_token = os.environ.get("OBSIDIAN_GITHUB_TOKEN")

    if not repo_url or not github_token:
        print("Obsidian sync requested but repository URL or token missing; skipping.")
        return

    call_with_outputs = _find_latest_structured_call()
    if not call_with_outputs:
        print("No completed morning call with structured outputs found; Obsidian sync skipped.")
        return

    artifact = getattr(call_with_outputs, "artifact", None)
    structured_outputs = getattr(artifact, "structured_outputs", {}) if artifact else {}
    goals = parse_goals_from_vapi_output(structured_outputs)
    if not goals:
        print("Structured outputs present but no goals parsed; Obsidian sync skipped.")
        return

    call_time = (
        _parse_vapi_datetime(getattr(call_with_outputs, "ended_at", None))
        or _parse_vapi_datetime(getattr(call_with_outputs, "started_at", None))
        or datetime.now()
    )

    call_data = {
        "id": getattr(call_with_outputs, "id", ""),
        "status": getattr(call_with_outputs, "status", ""),
    }

    try:
        with ObsidianGitSync(repo_url, github_token) as git_sync:
            obsidian = ObsidianSync(str(git_sync.vault_path), git_sync=git_sync)
            obsidian.create_morning_entry(goals, call_time, call_data)
        print("Obsidian vault updated with morning entry.")
    except Exception as exc:
        print(f"Obsidian sync failed: {exc}")


_sync_morning_to_obsidian()
