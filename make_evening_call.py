import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from vapi import Vapi

from obsidian_git_sync import ObsidianGitSync, ObsidianSync, parse_goals_from_vapi_output

# Load environment variables
VAPI_API_TOKEN = os.environ.get("VAPI_API_TOKEN")
MORNING_ASSISTANT_ID = os.environ.get("MORNING_ASSISTANT_ID")
EVENING_ASSISTANT_ID = os.environ.get("EVENING_ASSISTANT_ID")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
TARGET_PHONE_NUMBER = os.environ.get("TARGET_PHONE_NUMBER")

# Validate required environment variables
if not all(
    [
        VAPI_API_TOKEN,
        MORNING_ASSISTANT_ID,
        EVENING_ASSISTANT_ID,
        PHONE_NUMBER_ID,
        TARGET_PHONE_NUMBER,
    ]
):
    raise ValueError("Missing required environment variables. Please check .env file.")

client = Vapi(token=VAPI_API_TOKEN)


def _parse_vapi_datetime(timestamp: Optional[str]) -> Optional[datetime]:
    if not timestamp:
        return None
    value = timestamp.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _get_customer_number(call: object) -> Optional[str]:
    customer = getattr(call, "customer", None)
    if not customer:
        return None
    if isinstance(customer, dict):
        return customer.get("number")
    return getattr(customer, "number", None)


def _find_latest_structured_call(assistant_id: str) -> Optional[object]:
    calls_list = client.calls.list()
    for entry in calls_list:
        if (
            _get_customer_number(entry) == TARGET_PHONE_NUMBER
            and getattr(entry, "assistant_id", None) == assistant_id
            and getattr(entry, "status", None) == "ended"
        ):
            full_call = client.calls.get(id=entry.id)
            artifact = getattr(full_call, "artifact", None)
            structured_outputs = getattr(artifact, "structured_outputs", {}) if artifact else {}
            if structured_outputs:
                return full_call
    return None


def _build_evening_prompt(goals_text: str) -> str:
    return f"""Accountability Buddy AI - System Prompt
You are a supportive accountability buddy conducting brief daily check-ins via voice call. Your goal is to help users set intentions in the morning and reflect on progress in the evening.
Evening Call:

You will be provided with a numbered list of goals the user set this morning
below.

Morning Goals:
{goals_text}

Start with: "Hey, checking in! What are the things you accomplished today?"
As they share, mentally reference the morning list to see what they completed
If they mention completing items from the morning list, celebrate: "Awesome, you got [item] done!"
If they don't mention items from the morning list, gently prompt: "How about [item from morning]? Did you get to that?"
For incomplete items, ask non-judgmentally: "What got in the way?" or "What would help tomorrow?"
Don't lecture or criticize - be curious and supportive
End with: "Thanks for sharing. Rest well, and I'll talk to you tomorrow morning!"
Keep the call under 3-4 minutes

Tone:

Warm, encouraging friend (not a strict coach or therapist)
Conversational and natural
Brief and respectful of their time
Non-judgmental about setbacks"""


def _parse_evening_results(
    structured_outputs: Dict[str, object],
    goals: List[str],
) -> Tuple[List[bool], str]:
    """Derive completion booleans and reflections text from Vapi structured output."""
    completed = [False] * len(goals)
    reflections = ""

    if not structured_outputs:
        return completed, reflections

    def mark_goal(goal_text: str) -> None:
        for index, goal in enumerate(goals):
            if goal_text.lower() in goal.lower() or goal.lower() in goal_text.lower():
                completed[index] = True

    for key, value in structured_outputs.items():
        key_lower = str(key).lower()
        if isinstance(value, dict):
            if "completed" in value and "goal" in value:
                goal_text = str(value["goal"])
                if value["completed"]:
                    mark_goal(goal_text)
            if "result" in value and isinstance(value["result"], str):
                lines = value["result"].splitlines()
                for line in lines:
                    lower_line = line.lower()
                    if "reflection" in lower_line and not reflections:
                        reflections = line.split(":", 1)[-1].strip() if ":" in line else line.strip()
                        continue
                    if "complete" in lower_line or "[x]" in lower_line:
                        mark_goal(line)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    if item.get("completed"):
                        mark_goal(str(item.get("goal", "")))
                    if "reflections" in item and not reflections:
                        reflections = str(item["reflections"]).strip()
                elif isinstance(item, str):
                    lower_item = item.lower()
                    if "reflection" in lower_item and not reflections:
                        reflections = item.split(":", 1)[-1].strip() if ":" in item else item.strip()
                    if "complete" in lower_item or "[x]" in lower_item:
                        mark_goal(item)
        elif isinstance(value, str):
            lower_value = value.lower()
            if "reflection" in lower_value and not reflections:
                reflections = value.split(":", 1)[-1].strip() if ":" in value else value.strip()
            if "complete" in lower_value or "[x]" in lower_value:
                for line in value.splitlines():
                    if "complete" in line.lower() or "[x]" in line.lower():
                        mark_goal(line)

    return completed, reflections


def _sync_evening_to_obsidian(
    goals: List[str],
    completed: List[bool],
    call_time: datetime,
    reflections: str,
) -> None:
    obsidian_enabled = os.environ.get("OBSIDIAN_ENABLED", "false").lower() == "true"
    if not obsidian_enabled:
        print("Obsidian sync disabled; skipping evening vault update.")
        return

    repo_url = os.environ.get("OBSIDIAN_REPO_URL")
    github_token = os.environ.get("OBSIDIAN_GITHUB_TOKEN")

    if not repo_url or not github_token:
        print("Obsidian sync requested but repository URL or token missing; skipping.")
        return

    if not goals:
        print("No goals available to update evening entry; skipping Obsidian sync.")
        return

    try:
        with ObsidianGitSync(repo_url, github_token) as git_sync:
            obsidian = ObsidianSync(str(git_sync.vault_path), git_sync=git_sync)
            obsidian.update_evening_entry(goals, completed, call_time, reflections)
        print("Obsidian vault updated with evening review.")
    except Exception as exc:
        print(f"Obsidian evening sync failed: {exc}")


# ---------------------------------------------------------------------
# Locate the latest morning call with structured outputs (for context)

morning_call = _find_latest_structured_call(MORNING_ASSISTANT_ID)

if not morning_call:
    print(f"No successful morning calls with structured outputs found for {TARGET_PHONE_NUMBER}")
else:
    artifact = getattr(morning_call, "artifact", None)
    structured_outputs = getattr(artifact, "structured_outputs", {}) if artifact else {}

    print("Last successful morning call with structured outputs:")
    print(f"Call ID: {morning_call.id}")
    print(f"Call ended at: {morning_call.ended_at}")
    print("-" * 50)

    print("\nStructured Output Results:")
    print("-" * 50)
    goals_text_segments: List[str] = []
    for key, value in structured_outputs.items():
        if isinstance(value, dict):
            print(f"\nName: {value.get('name', 'N/A')}")
            print(f"Result:\n{value.get('result', 'N/A')}")
            goals_text_segments.append(str(value.get("result", "")))
        else:
            print(f"{key}: {value}")
            goals_text_segments.append(str(value))

    goals_text = "\n".join(segment for segment in goals_text_segments if segment).strip()
    goals_list = parse_goals_from_vapi_output(structured_outputs)

    print("\n" + "=" * 50)
    print("Creating new call with evening assistant...")
    print("=" * 50)

    # Create the evening system prompt with morning goals embedded
    evening_prompt = _build_evening_prompt(goals_text)
    print("\nFinal Evening Prompt with Morning Goals:")
    print("=" * 50)
    print(evening_prompt)
    print("=" * 50)

    # Update the evening assistant with the new prompt
    print("\nUpdating assistant...")
    updated_assistant = client.assistants.update(
        id=EVENING_ASSISTANT_ID,
        model={
            "provider": "openai",
            "model": "gpt-4o",
            "messages": [{"role": "system", "content": evening_prompt}],
        },
    )

    print("\nAssistant updated successfully!")
    print(f"Assistant ID: {updated_assistant.id}")
    print(f"Assistant name: {getattr(updated_assistant, 'name', 'N/A')}")

    # Now make the call using the updated evening assistant
    print("\n" + "=" * 50)
    print("Initiating evening call...")
    print("=" * 50)

    new_call = client.calls.create(
        assistant_id=EVENING_ASSISTANT_ID,
        phone_number_id=PHONE_NUMBER_ID,
        customer={"number": TARGET_PHONE_NUMBER},
    )

    print(f"\nEvening call initiated successfully!")
    print(f"Call ID: {new_call.id}")
    print(f"Status: {new_call.status}")
    print(f"Calling: {TARGET_PHONE_NUMBER}")
    print("Using updated evening assistant with morning goals")

    # Attempt to sync the most recent completed evening call to Obsidian
    evening_call = _find_latest_structured_call(EVENING_ASSISTANT_ID)
    if evening_call:
        evening_artifact = getattr(evening_call, "artifact", None)
        evening_outputs = (
            getattr(evening_artifact, "structured_outputs", {}) if evening_artifact else {}
        )
        completed_flags, reflections_text = _parse_evening_results(evening_outputs, goals_list)
        call_timestamp = (
            _parse_vapi_datetime(getattr(evening_call, "ended_at", None))
            or _parse_vapi_datetime(getattr(evening_call, "started_at", None))
            or datetime.now()
        )
        _sync_evening_to_obsidian(goals_list, completed_flags, call_timestamp, reflections_text)
    else:
        print("No previous evening call with structured outputs found; skipping Obsidian update.")
