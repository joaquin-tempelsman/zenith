#!/bin/bash

# Local Development Deployment Script
# Runs the application using Docker Compose for local development

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "════════════════════════════════════════════════════════"
echo "  🚀 Starting Local Development Environment"
echo "════════════════════════════════════════════════════════"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ Error: .env file not found${NC}"
    echo ""
    echo "Please create a .env file with the following variables:"
    echo "  OPENAI_API_KEY=your_key_here"
    echo "  TELEGRAM_BOT_TOKEN=your_token_here"
    echo "  DASHBOARD_PASSWORD=your_password_here"
    echo ""
    echo "You can copy .env.example to .env and fill in your values:"
    echo "  cp .env.example .env"
    exit 1
fi

echo -e "${BLUE}✅ Environment file found${NC}"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Docker is not running${NC}"
    echo "Please start Docker Desktop and try again"
    exit 1
fi

echo -e "${BLUE}✅ Docker is running${NC}"
echo ""

# Build and start services
echo -e "${YELLOW}Building Docker images...${NC}"
docker compose build

echo ""
echo -e "${YELLOW}Starting services...${NC}"
docker compose up -d

echo ""
echo -e "${YELLOW}Waiting for services to be healthy...${NC}"
sleep 5

# Check service health
if docker compose ps | grep -q "healthy"; then
    echo -e "${GREEN}✅ Services are running!${NC}"
else
    echo -e "${YELLOW}⚠️  Services are starting...${NC}"
fi

echo ""
echo "════════════════════════════════════════════════════════"
echo -e "${GREEN}✅ Local Development Environment Started!${NC}"
echo "════════════════════════════════════════════════════════"
echo ""
echo -e "${BLUE}Available URLs:${NC}"
echo "  📱 FastAPI:     http://localhost:8000"
echo "  📚 API Docs:    http://localhost:8000/docs"
echo "  🎨 Dashboard:   http://localhost:8501"
echo "  ❤️  Health:      http://localhost:8000/health"
echo ""
echo -e "${BLUE}Useful Commands:${NC}"
echo "  View logs:      docker compose logs -f"
echo "  Stop services:  docker compose down"
echo "  Restart:        docker compose restart"
echo "  Rebuild:        docker compose up -d --build"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop following logs, services will continue running${NC}"
echo ""

# Follow logs
docker compose logs -f

