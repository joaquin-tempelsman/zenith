#!/bin/bash

# Start ngrok, get the URL, and update Telegram webhook

echo "🚀 Starting ngrok..."
echo ""

# Start ngrok in the background
ngrok http 8000 > /tmp/ngrok.log 2>&1 &
NGROK_PID=$!

# Wait for ngrok to start
sleep 2

# Get the ngrok URL from ngrok's API
NGROK_URL=$(curl -s http://127.0.0.1:4040/api/tunnels | grep -o '"public_url":"https://[^"]*' | head -1 | cut -d'"' -f4)

if [ -z "$NGROK_URL" ]; then
    echo "❌ Failed to get ngrok URL. Make sure ngrok is installed and running."
    kill $NGROK_PID 2>/dev/null
    exit 1
fi

echo "✅ ngrok started successfully"
echo "🌐 Public URL: $NGROK_URL"
echo ""

# Build the webhook URL
WEBHOOK_URL="${NGROK_URL}/webhook"
echo "📨 Webhook URL: $WEBHOOK_URL"
echo ""

# Update the Telegram webhook using Python
echo "⏳ Updating Telegram webhook..."

uv run python << EOF
import sys
sys.path.insert(0, '$(pwd)')

from src.services.telegram import telegram_bot
from src.config import settings

webhook_url = "$WEBHOOK_URL"

try:
    response = telegram_bot.set_webhook(webhook_url)
    
    if response.get('ok'):
        print("✅ Telegram webhook updated successfully!")
        print(f"   Webhook URL: {webhook_url}")
        
        # Get and display webhook info
        webhook_info = telegram_bot.get_webhook_info()
        if webhook_info.get('ok'):
            print(f"   Pending updates: {webhook_info.get('result', {}).get('pending_update_count', 0)}")
    else:
        print(f"❌ Failed to update webhook: {response.get('description', 'Unknown error')}")
        sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
EOF

WEBHOOK_RESULT=$?

if [ $WEBHOOK_RESULT -eq 0 ]; then
    echo ""
    echo "════════════════════════════════════════════════════════"
    echo "  ✅ ngrok and Telegram webhook are ready!"
    echo "════════════════════════════════════════════════════════"
    echo ""
    echo "To stop ngrok, press Ctrl+C"
    echo ""
    # Keep ngrok running in foreground
    wait $NGROK_PID
else
    echo ""
    echo "❌ Failed to update Telegram webhook"
    kill $NGROK_PID 2>/dev/null
    exit 1
fi
