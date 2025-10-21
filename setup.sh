#!/bin/bash
set -e

echo "=================================================="
echo "Accountability Buddy - Environment Variable Check"
echo "=================================================="
echo ""

echo "GitHub Configuration:"
echo "  GITHUB_TOKEN: ${GITHUB_TOKEN:0:10}... (${#GITHUB_TOKEN} chars total)"
echo "  GITHUB_REPO: ${GITHUB_REPO}"
echo ""

echo "Vapi API Configuration:"
echo "  VAPI_API_TOKEN: ${VAPI_API_TOKEN:0:10}... (${#VAPI_API_TOKEN} chars total)"
echo ""

echo "Assistant IDs:"
echo "  MORNING_ASSISTANT_ID: ${MORNING_ASSISTANT_ID}"
echo "  EVENING_ASSISTANT_ID: ${EVENING_ASSISTANT_ID}"
echo ""

echo "Phone Configuration:"
echo "  PHONE_NUMBER_ID: ${PHONE_NUMBER_ID}"
echo "  TARGET_PHONE_NUMBER: ${TARGET_PHONE_NUMBER}"
echo ""

echo "Call Schedule:"
echo "  MORNING_CALL_TIME: ${MORNING_CALL_TIME}"
echo "  EVENING_CALL_TIME: ${EVENING_CALL_TIME}"
echo ""

echo "Timezone:"
echo "  TZ: ${TZ}"
echo ""

echo "=================================================="
echo "Checking for missing required variables..."
echo "=================================================="

MISSING=0

if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ GITHUB_TOKEN is not set!"
    MISSING=1
else
    echo "✓ GITHUB_TOKEN is set"
fi

if [ -z "$VAPI_API_TOKEN" ]; then
    echo "❌ VAPI_API_TOKEN is not set!"
    MISSING=1
else
    echo "✓ VAPI_API_TOKEN is set"
fi

if [ -z "$MORNING_ASSISTANT_ID" ]; then
    echo "❌ MORNING_ASSISTANT_ID is not set!"
    MISSING=1
else
    echo "✓ MORNING_ASSISTANT_ID is set"
fi

if [ -z "$EVENING_ASSISTANT_ID" ]; then
    echo "❌ EVENING_ASSISTANT_ID is not set!"
    MISSING=1
else
    echo "✓ EVENING_ASSISTANT_ID is set"
fi

if [ -z "$PHONE_NUMBER_ID" ]; then
    echo "❌ PHONE_NUMBER_ID is not set!"
    MISSING=1
else
    echo "✓ PHONE_NUMBER_ID is set"
fi

if [ -z "$TARGET_PHONE_NUMBER" ]; then
    echo "❌ TARGET_PHONE_NUMBER is not set!"
    MISSING=1
else
    echo "✓ TARGET_PHONE_NUMBER is set"
fi

echo ""
if [ $MISSING -eq 0 ]; then
    echo "=================================================="
    echo "✓ All required environment variables are set!"
    echo "=================================================="
    echo ""
    echo "Container will stay running for 10 minutes for you to check logs..."
    echo "Press Ctrl+C to exit early, or wait for auto-shutdown."
    sleep 600
else
    echo "=================================================="
    echo "❌ Some required variables are missing!"
    echo "Please check your .env file and try again."
    echo "=================================================="
    sleep 600
    exit 1
fi
