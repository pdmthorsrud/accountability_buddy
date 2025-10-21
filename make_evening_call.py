import os
from vapi import Vapi

# Load environment variables
VAPI_API_TOKEN = os.environ.get("VAPI_API_TOKEN")
MORNING_ASSISTANT_ID = os.environ.get("MORNING_ASSISTANT_ID")
EVENING_ASSISTANT_ID = os.environ.get("EVENING_ASSISTANT_ID")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
TARGET_PHONE_NUMBER = os.environ.get("TARGET_PHONE_NUMBER")

# Validate required environment variables
if not all([VAPI_API_TOKEN, MORNING_ASSISTANT_ID, EVENING_ASSISTANT_ID, PHONE_NUMBER_ID, TARGET_PHONE_NUMBER]):
    raise ValueError("Missing required environment variables. Please check .env file.")

client = Vapi(token=VAPI_API_TOKEN)

# Get list of all calls
calls_list = client.calls.list()

# Filter for calls to target number that were successful and from specific assistant
target_number = TARGET_PHONE_NUMBER
target_assistant_id = MORNING_ASSISTANT_ID
successful_calls = []

for call in calls_list:
    # Check if call has customer info and matches our number
    if hasattr(call, 'customer') and call.customer:
        customer_number = call.customer.get('number') if isinstance(call.customer, dict) else getattr(call.customer, 'number', None)

        # Check if call was successful (ended normally, not failed) and from our assistant
        if (customer_number == target_number and
            call.status == 'ended' and
            call.assistant_id == target_assistant_id):
            successful_calls.append(call)

if not successful_calls:
    print(f"No successful calls found for {target_number}")
else:
    # Search through calls to find one with structured outputs
    call_with_outputs = None

    for call in successful_calls:
        # Fetch full call details
        full_call = client.calls.get(id=call.id)

        # Check if it has structured outputs
        if hasattr(full_call, 'artifact') and full_call.artifact and hasattr(full_call.artifact, 'structured_outputs') and full_call.artifact.structured_outputs:
            call_with_outputs = full_call
            break

    if call_with_outputs:
        print(f"Last successful call with structured outputs:")
        print(f"Call ID: {call_with_outputs.id}")
        print(f"Call ended at: {call_with_outputs.ended_at}")
        print("-" * 50)

        # Print structured outputs from artifact
        print("\nStructured Output Results:")
        print("-" * 50)
        goals_text = ""
        for key, value in call_with_outputs.artifact.structured_outputs.items():
            if isinstance(value, dict):
                print(f"\nName: {value.get('name', 'N/A')}")
                print(f"Result:\n{value.get('result', 'N/A')}")
                goals_text = value.get('result', '')
            else:
                print(f"{key}: {value}")

        print("\n" + "=" * 50)
        print("Creating new call with evening assistant...")
        print("=" * 50)

        # Create new call with evening assistant and goals as context
        evening_assistant_id = EVENING_ASSISTANT_ID

        # Create the evening system prompt with morning goals embedded
        evening_prompt = f"""Accountability Buddy AI - System Prompt
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

        # Print the complete evening prompt with goals
        print("\nFinal Evening Prompt with Morning Goals:")
        print("=" * 50)
        print(evening_prompt)
        print("=" * 50)

        # Update the evening assistant with the new prompt
        print("\nUpdating assistant...")
        updated_assistant = client.assistants.update(
            id=evening_assistant_id,
            model={
                "provider": "openai",
                "model": "gpt-4o",
                "messages": [
                    {
                        "role": "system",
                        "content": evening_prompt
                    }
                ]
            }
        )

        print(f"\nAssistant updated successfully!")
        print(f"Assistant ID: {updated_assistant.id}")
        print(f"Assistant name: {updated_assistant.name if hasattr(updated_assistant, 'name') else 'N/A'}")

        # Now make the call using the updated evening assistant
        print("\n" + "=" * 50)
        print("Initiating evening call...")
        print("=" * 50)

        new_call = client.calls.create(
            assistant_id=evening_assistant_id,
            phone_number_id=PHONE_NUMBER_ID,
            customer={"number": target_number}
        )

        print(f"\nEvening call initiated successfully!")
        print(f"Call ID: {new_call.id}")
        print(f"Status: {new_call.status}")
        print(f"Calling: {target_number}")
        print(f"Using updated evening assistant with morning goals")

    else:
        print(f"Found {len(successful_calls)} successful call(s) to {target_number}, but none have structured outputs yet.")
        print(f"Most recent call ID: {successful_calls[0].id}")
