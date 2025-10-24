import os
from datetime import datetime, timezone
from typing import Optional

from vapi import Vapi

from obsidian_git_sync import ObsidianGitSync, ObsidianSync, parse_goals_from_vapi_output
from vapi_polling import (
    cron_reference_time,
    load_polling_configuration,
    parse_vapi_datetime,
    wait_for_structured_output,
)

# Load environment variables
VAPI_API_TOKEN = os.environ.get("VAPI_API_TOKEN")
MORNING_ASSISTANT_ID = os.environ.get("MORNING_ASSISTANT_ID")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
TARGET_PHONE_NUMBER = os.environ.get("TARGET_PHONE_NUMBER")
VAPI_SKIP_OUTBOUND_CALL = os.environ.get("VAPI_SKIP_OUTBOUND_CALL", "false").lower() == "true"
MORNING_CALL_TIME = os.environ.get("MORNING_CALL_TIME")

# Validate required environment variables
if not all([VAPI_API_TOKEN, MORNING_ASSISTANT_ID, PHONE_NUMBER_ID, TARGET_PHONE_NUMBER]):
    raise ValueError("Missing required environment variables. Please check .env file.")

client = Vapi(token=VAPI_API_TOKEN)

# Create outbound morning call
print("Initiating morning call...")
print("=" * 50)

if VAPI_SKIP_OUTBOUND_CALL:
    print("VAPI_SKIP_OUTBOUND_CALL=true; skipping outbound call creation for testing.")
else:
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


def _sync_morning_to_obsidian(call_with_outputs: Optional[object]) -> None:
    if not call_with_outputs:
        print("No completed morning call with structured outputs found; Obsidian sync skipped.")
        return

    obsidian_enabled = os.environ.get("OBSIDIAN_ENABLED", "false").lower() == "true"
    if not obsidian_enabled:
        print("Obsidian sync disabled; skipping vault update.")
        return

    repo_url = os.environ.get("OBSIDIAN_REPO_URL")
    github_token = os.environ.get("OBSIDIAN_GITHUB_TOKEN")

    if not repo_url or not github_token:
        print("Obsidian sync requested but repository URL or token missing; skipping.")
        return

    artifact = getattr(call_with_outputs, "artifact", None)
    structured_outputs = getattr(artifact, "structured_outputs", {}) if artifact else {}
    goals = parse_goals_from_vapi_output(structured_outputs)
    if not goals:
        print("Structured outputs present but no goals parsed; Obsidian sync skipped.")
        return

    call_time = (
        parse_vapi_datetime(getattr(call_with_outputs, "ended_at", None))
        or parse_vapi_datetime(getattr(call_with_outputs, "started_at", None))
        or datetime.now(timezone.utc)
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


poll_interval, timeout_delta, tolerance_delta = load_polling_configuration()
base_time = cron_reference_time(MORNING_CALL_TIME) or datetime.now(timezone.utc)

structured_call = wait_for_structured_output(
    client,
    assistant_id=MORNING_ASSISTANT_ID,
    target_number=TARGET_PHONE_NUMBER,
    base_time=base_time,
    poll_interval=poll_interval,
    timeout=timeout_delta,
    time_tolerance=tolerance_delta,
)

if structured_call:
    _sync_morning_to_obsidian(structured_call)
else:
    print(
        "No morning structured output available within the configured timeout; "
        "Obsidian sync skipped so it can be attempted later."
    )
