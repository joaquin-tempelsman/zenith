#!/bin/bash

# ════════════════════════════════════════════════════════
#  🚀 Start Development Environment
# ════════════════════════════════════════════════════════
# This script starts the inventory system in DEVELOPMENT mode
# - Uses TELEGRAM_BOT_TOKEN_DEV
# - Uses local database (./data/inventory.db)
# - Dashboard at http://localhost:8501
# - API at http://localhost:8000

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo ""
echo -e "${BOLD}════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  🚀 Starting DEVELOPMENT Environment${NC}"
echo -e "${BOLD}════════════════════════════════════════════════════════${NC}"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  Warning: .env file not found${NC}"
    echo "Please create a .env file with your configuration"
    exit 1
fi

# Ensure ENVIRONMENT is set to development
export ENVIRONMENT=development

echo -e "${BLUE}Environment:${NC} ${GREEN}DEVELOPMENT${NC}"
echo -e "${BLUE}Bot Token:${NC} Using TELEGRAM_BOT_TOKEN_DEV"
echo -e "${BLUE}Database:${NC} ./data/inventory.db (local)"
echo ""

# Stop any existing containers
echo -e "${YELLOW}Stopping existing containers...${NC}"
docker compose down

# Temporarily rename override file to prevent it from being used in dev
if [ -f docker-compose.override.yml ]; then
    echo -e "${YELLOW}Temporarily disabling production override...${NC}"
    mv docker-compose.override.yml docker-compose.override.yml.disabled
fi

echo ""
echo -e "${YELLOW}Starting services...${NC}"
docker compose up -d

# Restore override file
if [ -f docker-compose.override.yml.disabled ]; then
    mv docker-compose.override.yml.disabled docker-compose.override.yml
fi

echo ""
echo -e "${YELLOW}Waiting for services to be ready (15 seconds)...${NC}"
sleep 15

# Check service health
echo ""
echo -e "${YELLOW}Checking service health...${NC}"

if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ API is healthy!${NC}"
else
    echo -e "${YELLOW}⚠️  API health check failed (may still be starting)${NC}"
fi

if curl -f http://localhost:8501 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Dashboard is accessible!${NC}"
else
    echo -e "${YELLOW}⚠️  Dashboard health check failed (may still be starting)${NC}"
fi

# Check ngrok
if curl -f http://localhost:4040/api/tunnels > /dev/null 2>&1; then
    echo -e "${GREEN}✅ ngrok tunnel is running!${NC}"
    NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['tunnels'][0]['public_url'] if data.get('tunnels') else 'Not available')" 2>/dev/null || echo "Not available")
    echo -e "${BLUE}   Public URL:${NC} $NGROK_URL"
else
    echo -e "${YELLOW}⚠️  ngrok not accessible yet${NC}"
fi

echo ""
echo -e "${BOLD}════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  ✅ Development Environment Started!${NC}"
echo -e "${BOLD}════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}Access URLs:${NC}"
echo "  Dashboard:     http://localhost:8501"
echo "  API:           http://localhost:8000"
echo "  API Docs:      http://localhost:8000/docs"
echo "  ngrok Web UI:  http://localhost:4040"
echo ""
echo -e "${BLUE}Telegram Bot:${NC}"
echo "  Using: ${GREEN}DEV bot${NC} (TELEGRAM_BOT_TOKEN_DEV)"
echo "  Send messages to your DEV bot to test"
echo ""
echo -e "${BLUE}Useful Commands:${NC}"
echo "  View logs:        docker compose logs -f"
echo "  View API logs:    docker compose logs -f api"
echo "  Stop services:    docker compose down"
echo "  Restart:          docker compose restart"
echo ""
echo -e "${YELLOW}Note: Messages sent to your DEV Telegram bot will appear in the local dashboard${NC}"
echo ""

