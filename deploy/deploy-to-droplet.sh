#!/bin/bash

# Deploy to DigitalOcean Droplet
# This script should be run ON the droplet after code is pulled

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "════════════════════════════════════════════════════════"
echo "  🚀 Deploying to DigitalOcean Droplet (PRODUCTION)"
echo "════════════════════════════════════════════════════════"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Ensure ENVIRONMENT is set to production
export ENVIRONMENT=production

echo -e "${BLUE}Environment:${NC} ${GREEN}PRODUCTION${NC}"
echo -e "${BLUE}Bot Token:${NC} Using TELEGRAM_BOT_TOKEN_PROD"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ Error: .env file not found${NC}"
    echo "Please create a .env file with production credentials"
    exit 1
fi

echo -e "${BLUE}✅ Environment file found${NC}"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Docker is not running${NC}"
    exit 1
fi

echo -e "${BLUE}✅ Docker is running${NC}"
echo ""

# Create data directory with proper permissions
echo -e "${YELLOW}Setting up data directory...${NC}"
mkdir -p data
chmod 777 data

echo ""
echo -e "${YELLOW}Building Docker images...${NC}"
docker compose build

echo ""
echo -e "${YELLOW}Cleaning up build cache to free disk space...${NC}"
echo "This is important for small droplets with limited disk space"
docker builder prune -af
docker system prune -f

echo ""
echo -e "${YELLOW}Stopping existing services...${NC}"
docker compose down

echo ""
echo -e "${YELLOW}Starting services (including ngrok for Telegram webhook)...${NC}"
docker compose up -d api dashboard ngrok

echo ""
echo -e "${YELLOW}Waiting for services to start (30 seconds)...${NC}"
sleep 30

# Check service health
echo ""
echo -e "${YELLOW}Checking service health...${NC}"
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ API is healthy!${NC}"
else
    echo -e "${RED}❌ API health check failed${NC}"
    echo "Showing API logs:"
    docker compose logs api --tail=30
    exit 1
fi

if curl -f http://localhost:8501 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Dashboard is accessible!${NC}"
else
    echo -e "${YELLOW}⚠️  Dashboard health check failed (may still be starting)${NC}"
fi

echo ""
echo -e "${YELLOW}Setting up Telegram webhook with ngrok...${NC}"
# Run webhook setup container
docker compose run --rm webhook-setup

echo ""
echo -e "${YELLOW}Cleaning up old/unused images...${NC}"
docker image prune -af

echo ""
echo "════════════════════════════════════════════════════════"
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo "════════════════════════════════════════════════════════"
echo ""
echo -e "${BLUE}Service Status:${NC}"
docker compose ps
echo ""
echo -e "${BLUE}Resource Usage:${NC}"
docker stats --no-stream
echo ""
echo -e "${BLUE}Disk Usage:${NC}"
df -h / | grep -v Filesystem
echo ""
echo -e "${BLUE}Memory Usage:${NC}"
free -h | grep -v total
echo ""
echo -e "${BLUE}Useful Commands:${NC}"
echo "  View logs:      docker compose logs -f"
echo "  View API logs:  docker compose logs -f api"
echo "  Stop services:  docker compose down"
echo "  Restart:        docker compose restart"
echo "  Check status:   docker compose ps"
echo ""
echo -e "${YELLOW}Note: For small droplets (512MB RAM), monitor memory usage regularly${NC}"
echo "  Check memory:   free -h"
echo "  Check disk:     df -h"
echo "  Clean Docker:   docker system prune -af"
echo ""

