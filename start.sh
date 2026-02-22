#!/bin/bash

# Master startup script for Voice-Managed Inventory System
# Launches FastAPI server, ngrok tunnel, and dashboard in separate terminals

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "════════════════════════════════════════════════════════"
echo "  🚀 Starting Voice-Managed Inventory System"
echo "════════════════════════════════════════════════════════"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to open terminal on macOS
open_terminal() {
    local title="$1"
    local command="$2"
    
    osascript <<EOF
tell application "Terminal"
    activate
    do script "cd '$PROJECT_DIR' && $command"
end tell
EOF
    echo -e "${GREEN}✅${NC} Opened terminal: ${BLUE}$title${NC}"
}

# Function to open terminal for non-macOS (Linux/WSL)
open_terminal_generic() {
    local title="$1"
    local command="$2"
    
    # Try common terminal emulators
    if command -v gnome-terminal &> /dev/null; then
        gnome-terminal -- bash -c "cd '$PROJECT_DIR' && $command; exec bash"
    elif command -v xterm &> /dev/null; then
        xterm -title "$title" -e "cd '$PROJECT_DIR' && $command; bash" &
    elif command -v konsole &> /dev/null; then
        konsole --title "$title" -e bash -c "cd '$PROJECT_DIR' && $command; exec bash" &
    else
        echo -e "${YELLOW}⚠️  Could not detect terminal emulator. Running in current shell.${NC}"
        eval "$command"
    fi
    echo -e "${GREEN}✅${NC} Opened terminal: ${BLUE}$title${NC}"
}

# Determine OS and use appropriate terminal opener
if [[ "$OSTYPE" == "darwin"* ]]; then
    OPEN_TERMINAL="open_terminal"
else
    OPEN_TERMINAL="open_terminal_generic"
fi

echo -e "${YELLOW}Starting services...${NC}"
echo ""

# 1. Start FastAPI Server
echo -e "${BLUE}1️⃣  FastAPI Server${NC}"
echo "   Starting on: http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"
$OPEN_TERMINAL "FastAPI Server" "bash $PROJECT_DIR/start_api.sh"
sleep 2

# 2. Start ngrok Webhook
echo ""
echo -e "${BLUE}2️⃣  ngrok Tunnel${NC}"
echo "   Setting up webhook tunnel..."
$OPEN_TERMINAL "ngrok Webhook" "bash $PROJECT_DIR/start_ngrok_webhook.sh"
sleep 3

# 3. Start Dashboard (optional)
echo ""
echo -e "${BLUE}3️⃣  Streamlit Dashboard${NC}"
echo "   Starting on: http://localhost:8501"
$OPEN_TERMINAL "Dashboard" "bash $PROJECT_DIR/start_dashboard.sh"

echo ""
echo "════════════════════════════════════════════════════════"
echo -e "${GREEN}✅ All services started!${NC}"
echo "════════════════════════════════════════════════════════"
echo ""
echo -e "${BLUE}Available URLs:${NC}"
echo "  📱 FastAPI:  http://localhost:8000"
echo "  📚 API Docs: http://localhost:8000/docs"
echo "  🎨 Dashboard: http://localhost:8501"
echo ""
echo -e "${BLUE}Services running in separate terminals:${NC}"
echo "  • FastAPI Server (start_api.sh)"
echo "  • ngrok Tunnel (start_ngrok_webhook.sh)"
echo "  • Streamlit Dashboard (start_dashboard.sh)"
echo ""
echo -e "${YELLOW}To stop all services, close the terminal windows or press Ctrl+C${NC}"
echo ""
