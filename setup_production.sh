#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR"

echo "=================================================="
echo "Accountability Buddy - Container Setup"
echo "=================================================="

# Validate required environment variables
if [ -z "$VAPI_API_TOKEN" ] || [ -z "$MORNING_ASSISTANT_ID" ] || [ -z "$EVENING_ASSISTANT_ID" ] || [ -z "$PHONE_NUMBER_ID" ] || [ -z "$TARGET_PHONE_NUMBER" ]; then
    echo "ERROR: Missing required environment variables!"
    echo "Please ensure all required environment variables are set:"
    echo "  - VAPI_API_TOKEN"
    echo "  - MORNING_ASSISTANT_ID"
    echo "  - EVENING_ASSISTANT_ID"
    echo "  - PHONE_NUMBER_ID"
    echo "  - TARGET_PHONE_NUMBER"
    exit 1
fi

echo "✓ Environment variables validated"

# Install Python dependencies
echo "Installing Python dependencies..."
python3 -m pip install --no-cache-dir -r "$APP_DIR/requirements.txt"
echo "✓ Python dependencies installed"

# Set default times if not provided
MORNING_CALL_TIME="${MORNING_CALL_TIME:-0 8 * * *}"
EVENING_CALL_TIME="${EVENING_CALL_TIME:-0 20 * * *}"

echo "Setting up cron jobs..."
echo "  Morning call: $MORNING_CALL_TIME"
echo "  Evening call: $EVENING_CALL_TIME"

# Create cron jobs
cat > /etc/cron.d/accountability-buddy << EOF
# Accountability Buddy Cron Jobs
SHELL=/bin/bash
PATH=/usr/local/bin:/usr/bin:/bin
APP_DIR=$APP_DIR
VAPI_API_TOKEN=$VAPI_API_TOKEN
MORNING_ASSISTANT_ID=$MORNING_ASSISTANT_ID
EVENING_ASSISTANT_ID=$EVENING_ASSISTANT_ID
PHONE_NUMBER_ID=$PHONE_NUMBER_ID
TARGET_PHONE_NUMBER=$TARGET_PHONE_NUMBER

# Morning call
$MORNING_CALL_TIME root cd "\$APP_DIR" && python3 make_morning_call.py >> /var/log/morning_call.log 2>&1

# Evening call
$EVENING_CALL_TIME root cd "\$APP_DIR" && python3 make_evening_call.py >> /var/log/evening_call.log 2>&1
EOF

# Set proper permissions for cron file
chmod 0644 /etc/cron.d/accountability-buddy

# Create log files
touch /var/log/morning_call.log /var/log/evening_call.log
chmod 0666 /var/log/morning_call.log /var/log/evening_call.log

echo "✓ Cron jobs configured"

# Apply cron jobs
crontab /etc/cron.d/accountability-buddy
echo "✓ Crontab installed"

echo "=================================================="
echo "Setup complete!"
echo "=================================================="
echo "Cron schedule:"
echo "  Morning: $MORNING_CALL_TIME"
echo "  Evening: $EVENING_CALL_TIME"
echo ""
echo "Logs available at:"
echo "  /var/log/morning_call.log"
echo "  /var/log/evening_call.log"
echo "=================================================="

# Start cron in foreground
echo "Starting cron service..."
exec cron -f
