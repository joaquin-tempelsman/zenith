#!/bin/bash

# Quick Start Script for Docker Development
# This script provides an easy way to start the application with Docker

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "════════════════════════════════════════════════════════"
echo "  🚀 Voice-Managed Inventory System - Docker Quick Start"
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
    echo -e "${YELLOW}⚠️  No .env file found. Creating from .env.example...${NC}"
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${GREEN}✅ Created .env file${NC}"
        echo ""
        echo -e "${RED}⚠️  IMPORTANT: Please edit .env and add your API keys before continuing!${NC}"
        echo ""
        echo "Required variables:"
        echo "  - OPENAI_API_KEY"
        echo "  - TELEGRAM_BOT_TOKEN"
        echo "  - DASHBOARD_PASSWORD"
        echo ""
        read -p "Press Enter after you've updated .env, or Ctrl+C to exit..."
    else
        echo -e "${RED}❌ Error: .env.example not found${NC}"
        exit 1
    fi
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Docker is not running${NC}"
    echo "Please start Docker Desktop and try again"
    exit 1
fi

echo -e "${GREEN}✅ Docker is running${NC}"
echo ""

# Ask user which environment
echo -e "${BLUE}Which environment do you want to start?${NC}"
echo "  1) Development (with hot-reload)"
echo "  2) Production (optimized)"
echo ""
read -p "Enter choice [1-2]: " choice

case $choice in
    1)
        echo ""
        echo -e "${YELLOW}Starting Development Environment with ngrok...${NC}"
        echo ""

        # Build images
        echo -e "${BLUE}Building Docker images...${NC}"
        docker compose build

        # Start services with dev profile (includes ngrok and webhook setup)
        echo ""
        echo -e "${BLUE}Starting services (API, Dashboard, ngrok, webhook setup)...${NC}"
        docker compose --profile dev up -d

        # Wait for services to start
        echo ""
        echo -e "${BLUE}Waiting for services to be ready...${NC}"
        sleep 8

        # Check webhook setup logs
        echo ""
        echo -e "${BLUE}Checking webhook setup...${NC}"
        docker logs inventory-webhook-setup 2>/dev/null || echo "Webhook setup in progress..."

        echo ""
        echo "════════════════════════════════════════════════════════"
        echo -e "${GREEN}✅ Development Environment Started!${NC}"
        echo "════════════════════════════════════════════════════════"
        echo ""
        echo -e "${BLUE}Available URLs:${NC}"
        echo "  📱 FastAPI:        http://localhost:8000"
        echo "  📚 API Docs:       http://localhost:8000/docs"
        echo "  🎨 Dashboard:      http://localhost:8501"
        echo "  🌐 ngrok Dashboard: http://localhost:4040"
        echo "  ❤️  Health:         http://localhost:8000/health"
        echo ""
        echo -e "${BLUE}Telegram Webhook:${NC}"
        echo "  Check status:   curl http://localhost:8000/webhook-info"
        echo "  Setup logs:     docker logs inventory-webhook-setup"
        echo ""
        echo -e "${BLUE}Useful Commands:${NC}"
        echo "  View logs:      docker compose --profile dev logs -f"
        echo "  Stop services:  docker compose --profile dev down"
        echo "  Restart:        docker compose --profile dev restart"
        echo ""

        # Ask if user wants to follow logs
        read -p "Follow logs? [y/N]: " follow_logs
        if [[ $follow_logs =~ ^[Yy]$ ]]; then
            docker compose --profile dev logs -f
        fi
        ;;
        
    2)
        echo ""
        echo -e "${YELLOW}Starting Production Environment...${NC}"
        echo ""
        
        # Build images
        echo -e "${BLUE}Building production Docker images...${NC}"
        docker compose -f docker/docker-compose.prod.yml build

        # Start services
        echo ""
        echo -e "${BLUE}Starting production services...${NC}"
        docker compose -f docker/docker-compose.prod.yml up -d
        
        # Wait for health check
        echo ""
        echo -e "${BLUE}Waiting for services to be ready...${NC}"
        sleep 10
        
        # Check health
        if curl -f http://localhost:8000/health > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Health check passed!${NC}"
        else
            echo -e "${YELLOW}⚠️  Health check pending...${NC}"
        fi
        
        echo ""
        echo "════════════════════════════════════════════════════════"
        echo -e "${GREEN}✅ Production Environment Started!${NC}"
        echo "════════════════════════════════════════════════════════"
        echo ""
        echo -e "${BLUE}Available URLs:${NC}"
        echo "  📱 FastAPI:     http://localhost:8000"
        echo "  📚 API Docs:    http://localhost:8000/docs"
        echo "  🎨 Dashboard:   http://localhost:8501"
        echo ""
        echo -e "${BLUE}Useful Commands:${NC}"
        echo "  View logs:      docker compose -f docker/docker-compose.prod.yml logs -f"
        echo "  Stop services:  docker compose -f docker/docker-compose.prod.yml down"
        echo "  Restart:        docker compose -f docker/docker-compose.prod.yml restart"
        echo ""

        # Ask if user wants to follow logs
        read -p "Follow logs? [y/N]: " follow_logs
        if [[ $follow_logs =~ ^[Yy]$ ]]; then
            docker compose -f docker/docker-compose.prod.yml logs -f
        fi
        ;;
        
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

