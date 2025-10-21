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

## Docker Deployment (Recommended)

The easiest way to run this project is using Docker Compose. This automatically sets up everything including cron jobs.

### Quick Start with Docker

1. **Create a GitHub Personal Access Token** (for private repo access):
   - Go to https://github.com/settings/tokens
   - Click "Generate new token" → "Generate new token (classic)"
   - Give it a name like "Accountability Buddy Docker"
   - Select scope: `repo` (Full control of private repositories)
   - Click "Generate token" and copy it

2. **Clone the repository** (or pull it via Docker):
```bash
git clone https://github.com/pdmthorsrud/accountability_buddy.git
cd accountability_buddy
```

3. **Create environment file**:
```bash
cp .env.docker .env
```

Edit `.env` and fill in your actual values:
```bash
# GitHub token for private repo access
GITHUB_TOKEN=ghp_your_github_token_here

# Vapi configuration
VAPI_API_TOKEN=your_actual_token
MORNING_ASSISTANT_ID=your_morning_assistant_id
EVENING_ASSISTANT_ID=your_evening_assistant_id
PHONE_NUMBER_ID=your_phone_number_id
TARGET_PHONE_NUMBER=+1234567890

# Optional: Customize call times (cron format)
MORNING_CALL_TIME=0 8 * * *    # 8:00 AM
EVENING_CALL_TIME=0 20 * * *   # 8:00 PM

# Optional: Set your timezone
TZ=Europe/Oslo
```

4. **Start the container**:
```bash
docker-compose up -d
```

5. **View logs**:
```bash
# Container logs
docker-compose logs -f

# Call logs (if volume mounted)
tail -f logs/morning_call.log
tail -f logs/evening_call.log
```

6. **Stop the container**:
```bash
docker-compose down
```

### Unraid Setup

1. In Unraid, go to **Docker** tab
2. Click **Add Container**
3. Fill in:
   - **Name**: `accountability-buddy`
   - **Repository**: Build from your cloned repo or use pre-built image
   - **Environment Variables**: Add all required vars from `.env.docker`
   - **Console Shell**: `bash`

The container will automatically:
- Clone the latest code from GitHub
- Install dependencies
- Set up cron jobs for morning and evening calls
- Start running in the background

### Customizing Call Times

Call times use standard cron format: `minute hour day month weekday`

Examples:
- `0 8 * * *` - 8:00 AM every day
- `30 7 * * 1-5` - 7:30 AM on weekdays only
- `0 20 * * *` - 8:00 PM every day
- `0 21 * * 0,6` - 9:00 PM on weekends only

### Manual Scheduling (Non-Docker)

If not using Docker, use cron directly:

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
├── setup.sh                # Container setup script
├── Dockerfile              # Docker container definition
├── docker-compose.yml      # Docker Compose configuration
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variable template (local)
├── .env.docker            # Environment variable template (Docker)
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
