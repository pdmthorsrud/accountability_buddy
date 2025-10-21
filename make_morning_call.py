import os
from vapi import Vapi

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
