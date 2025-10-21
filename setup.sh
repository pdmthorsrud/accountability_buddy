#!/bin/bash
set -e

# Log file
LOG_FILE="/var/log/setup_check.log"

# Function to log to both stdout and file
log() {
    echo "$1" | tee -a "$LOG_FILE"
}

log "=================================================="
log "Accountability Buddy - Environment Variable Check"
log "=================================================="
log ""

log "GitHub Configuration:"
log "  GITHUB_TOKEN: ${GITHUB_TOKEN:0:10}... (${#GITHUB_TOKEN} chars total)"
log "  GITHUB_REPO: ${GITHUB_REPO}"
log ""

log "Vapi API Configuration:"
log "  VAPI_API_TOKEN: ${VAPI_API_TOKEN:0:10}... (${#VAPI_API_TOKEN} chars total)"
log ""

log "Assistant IDs:"
log "  MORNING_ASSISTANT_ID: ${MORNING_ASSISTANT_ID}"
log "  EVENING_ASSISTANT_ID: ${EVENING_ASSISTANT_ID}"
log ""

log "Phone Configuration:"
log "  PHONE_NUMBER_ID: ${PHONE_NUMBER_ID}"
log "  TARGET_PHONE_NUMBER: ${TARGET_PHONE_NUMBER}"
log ""

log "Call Schedule:"
log "  MORNING_CALL_TIME: ${MORNING_CALL_TIME}"
log "  EVENING_CALL_TIME: ${EVENING_CALL_TIME}"
log ""

log "Timezone:"
log "  TZ: ${TZ}"
log ""

log "=================================================="
log "Checking for missing required variables..."
log "=================================================="

MISSING=0

if [ -z "$GITHUB_TOKEN" ]; then
    log "❌ GITHUB_TOKEN is not set!"
    MISSING=1
else
    log "✓ GITHUB_TOKEN is set"
fi

if [ -z "$VAPI_API_TOKEN" ]; then
    log "❌ VAPI_API_TOKEN is not set!"
    MISSING=1
else
    log "✓ VAPI_API_TOKEN is set"
fi

if [ -z "$MORNING_ASSISTANT_ID" ]; then
    log "❌ MORNING_ASSISTANT_ID is not set!"
    MISSING=1
else
    log "✓ MORNING_ASSISTANT_ID is set"
fi

if [ -z "$EVENING_ASSISTANT_ID" ]; then
    log "❌ EVENING_ASSISTANT_ID is not set!"
    MISSING=1
else
    log "✓ EVENING_ASSISTANT_ID is set"
fi

if [ -z "$PHONE_NUMBER_ID" ]; then
    log "❌ PHONE_NUMBER_ID is not set!"
    MISSING=1
else
    log "✓ PHONE_NUMBER_ID is set"
fi

if [ -z "$TARGET_PHONE_NUMBER" ]; then
    log "❌ TARGET_PHONE_NUMBER is not set!"
    MISSING=1
else
    log "✓ TARGET_PHONE_NUMBER is set"
fi

log ""
if [ $MISSING -eq 0 ]; then
    log "=================================================="
    log "✓ All required environment variables are set!"
    log "=================================================="
    log ""
    log "Log file saved to: $LOG_FILE"
    log "Container will stay running for 10 minutes for you to check logs..."
    log "Press Ctrl+C to exit early, or wait for auto-shutdown."
    sleep 600
else
    log "=================================================="
    log "❌ Some required variables are missing!"
    log "Please check your .env file and try again."
    log "=================================================="
    sleep 600
    exit 1
fi
