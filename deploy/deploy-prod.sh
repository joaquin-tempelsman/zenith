#!/bin/bash

# Production Deployment Script
# Deploy to Digital Ocean or any cloud VM

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "════════════════════════════════════════════════════════"
echo "  🚀 Production Deployment"
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

# Pull latest code
echo -e "${YELLOW}Pulling latest code...${NC}"
git pull origin main || echo "Not a git repository or no remote configured"

echo ""
echo -e "${YELLOW}Building production images...${NC}"
docker compose -f docker-compose.prod.yml build --no-cache

echo ""
echo -e "${YELLOW}Stopping existing services...${NC}"
docker compose -f docker-compose.prod.yml down

echo ""
echo -e "${YELLOW}Starting production services...${NC}"
docker compose -f docker-compose.prod.yml up -d

echo ""
echo -e "${YELLOW}Waiting for services to be healthy...${NC}"
sleep 10

# Check service health
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ API is healthy!${NC}"
else
    echo -e "${RED}❌ API health check failed${NC}"
    docker compose -f docker-compose.prod.yml logs api
    exit 1
fi

echo ""
echo -e "${YELLOW}Cleaning up old images...${NC}"
docker image prune -af

echo ""
echo "════════════════════════════════════════════════════════"
echo -e "${GREEN}✅ Production Deployment Complete!${NC}"
echo "════════════════════════════════════════════════════════"
echo ""
echo -e "${BLUE}Service Status:${NC}"
docker compose -f docker-compose.prod.yml ps
echo ""
echo -e "${BLUE}Useful Commands:${NC}"
echo "  View logs:      docker compose -f docker-compose.prod.yml logs -f"
echo "  Stop services:  docker compose -f docker-compose.prod.yml down"
echo "  Restart:        docker compose -f docker-compose.prod.yml restart"
echo ""

