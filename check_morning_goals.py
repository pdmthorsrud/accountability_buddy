import os
from vapi import Vapi

# Load environment variables
VAPI_API_TOKEN = os.environ.get("VAPI_API_TOKEN")
MORNING_ASSISTANT_ID = os.environ.get("MORNING_ASSISTANT_ID")
TARGET_PHONE_NUMBER = os.environ.get("TARGET_PHONE_NUMBER")

# Validate required environment variables
if not all([VAPI_API_TOKEN, MORNING_ASSISTANT_ID, TARGET_PHONE_NUMBER]):
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
        for key, value in call_with_outputs.artifact.structured_outputs.items():
            if isinstance(value, dict):
                print(f"\nName: {value.get('name', 'N/A')}")
                print(f"Result:\n{value.get('result', 'N/A')}")
            else:
                print(f"{key}: {value}")

    else:
        print(f"Found {len(successful_calls)} successful call(s) to {target_number}, but none have structured outputs yet.")
        if successful_calls:
            print(f"Most recent call ID: {successful_calls[0].id}")
