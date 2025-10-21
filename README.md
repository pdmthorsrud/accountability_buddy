# Accountability Buddy

An automated accountability system using [Vapi](https://vapi.ai) for daily morning and evening voice call check-ins.

## Overview

This project provides automated accountability check-ins via phone calls:
- **Morning calls**: Sets your daily intentions and goals
- **Evening calls**: Reviews progress on your morning goals

The system uses Vapi's AI voice assistants to conduct natural, supportive conversations that help you stay on track with your daily objectives.

## Features

- 🌅 **Morning Check-in**: AI assistant asks about your plans and captures your goals for the day
- 🌙 **Evening Check-in**: Reviews your morning goals and celebrates wins or discusses obstacles
- 📊 **Structured Output**: Automatically extracts and stores your goals from conversations
- 🔄 **Contextual Follow-up**: Evening calls reference your specific morning goals

## Setup

### Prerequisites

- Python 3.9+
- [Vapi](https://vapi.ai) account with API access
- Two Vapi assistants (morning and evening)
- Vapi phone number configured

### Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Required variables:
- `VAPI_API_TOKEN`: Your Vapi API token
- `MORNING_ASSISTANT_ID`: ID of your morning accountability assistant
- `EVENING_ASSISTANT_ID`: ID of your evening accountability assistant
- `PHONE_NUMBER_ID`: Your Vapi phone number ID
- `TARGET_PHONE_NUMBER`: The phone number to call (E.164 format, e.g., +1234567890)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/accountability_buddy.git
cd accountability_buddy
```

2. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Making a Morning Call

Initiates a call to set your daily goals:

```bash
python make_morning_call.py
```

### Checking Morning Goals

View the structured output from your last morning call:

```bash
python check_morning_goals.py
```

### Making an Evening Call

Automatically:
1. Retrieves your morning goals from the last successful call
2. Updates the evening assistant with those goals
3. Initiates an evening check-in call

```bash
python make_evening_call.py
```

## Docker Deployment

For deployment on Unraid or other container platforms:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY *.py .

# Set environment variables in your container configuration
ENV VAPI_API_TOKEN=""
ENV MORNING_ASSISTANT_ID=""
ENV EVENING_ASSISTANT_ID=""
ENV PHONE_NUMBER_ID=""
ENV TARGET_PHONE_NUMBER=""

CMD ["python", "make_morning_call.py"]
```

## Scheduling

Use cron or your container scheduler to run calls at specific times:

```cron
# Morning call at 8:00 AM
0 8 * * * cd /path/to/accountability_buddy && source .venv/bin/activate && python make_morning_call.py

# Evening call at 8:00 PM
0 20 * * * cd /path/to/accountability_buddy && source .venv/bin/activate && python make_evening_call.py
```

## Project Structure

```
accountability_buddy/
├── make_morning_call.py    # Initiates morning accountability call
├── make_evening_call.py    # Updates evening assistant and makes call
├── check_morning_goals.py  # Displays structured output from last call
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variable template
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

## How It Works

1. **Morning Flow**:
   - `make_morning_call.py` initiates a call using the morning assistant
   - The assistant asks about your plans for the day
   - Vapi's structured output feature extracts your goals as a numbered list

2. **Evening Flow**:
   - `make_evening_call.py` retrieves the last successful morning call
   - Extracts the structured output (your goals)
   - Updates the evening assistant's system prompt with your specific goals
   - Initiates an evening call where the assistant references your morning commitments

## License

MIT License - feel free to use and modify for your own accountability needs!

## Contributing

Pull requests welcome! Please ensure your code follows the existing style and includes appropriate error handling.
