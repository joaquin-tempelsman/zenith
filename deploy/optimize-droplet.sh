#!/bin/bash

# Optimize DigitalOcean Droplet
# Run this script to clean up and optimize a running droplet

set -e

echo "════════════════════════════════════════════════════════"
echo "  🧹 Optimizing DigitalOcean Droplet"
echo "════════════════════════════════════════════════════════"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Current Resource Usage:${NC}"
echo ""
echo "Memory:"
free -h
echo ""
echo "Disk:"
df -h /
echo ""
echo "Docker:"
docker system df
echo ""

echo -e "${YELLOW}Starting optimization...${NC}"
echo ""

# 1. Clean Docker build cache
echo -e "${BLUE}1️⃣  Cleaning Docker build cache...${NC}"
BEFORE_BUILD=$(docker system df --format "{{.BuildCache}}" | awk '{print $1}')
docker builder prune -af
echo -e "${GREEN}✅ Build cache cleaned${NC}"
echo ""

# 2. Clean Docker system (unused containers, networks, images)
echo -e "${BLUE}2️⃣  Cleaning Docker system...${NC}"
docker system prune -f
echo -e "${GREEN}✅ Docker system cleaned${NC}"
echo ""

# 3. Remove dangling images
echo -e "${BLUE}3️⃣  Removing dangling images...${NC}"
docker image prune -f
echo -e "${GREEN}✅ Dangling images removed${NC}"
echo ""

# 4. Clean apt cache (if running as root)
if [ "$EUID" -eq 0 ]; then
    echo -e "${BLUE}4️⃣  Cleaning apt cache...${NC}"
    apt-get clean
    apt-get autoclean
    apt-get autoremove -y
    echo -e "${GREEN}✅ Apt cache cleaned${NC}"
else
    echo -e "${YELLOW}⚠️  Skipping apt cache cleanup (requires root)${NC}"
    echo "   Run with sudo to clean apt cache"
fi
echo ""

# 5. Clean journal logs (if running as root)
if [ "$EUID" -eq 0 ]; then
    echo -e "${BLUE}5️⃣  Cleaning old journal logs...${NC}"
    journalctl --vacuum-time=7d
    echo -e "${GREEN}✅ Journal logs cleaned${NC}"
else
    echo -e "${YELLOW}⚠️  Skipping journal cleanup (requires root)${NC}"
    echo "   Run with sudo to clean journal logs"
fi
echo ""

echo "════════════════════════════════════════════════════════"
echo -e "${GREEN}✅ Optimization Complete!${NC}"
echo "════════════════════════════════════════════════════════"
echo ""

echo -e "${BLUE}Updated Resource Usage:${NC}"
echo ""
echo "Memory:"
free -h
echo ""
echo "Disk:"
df -h /
echo ""
echo "Docker:"
docker system df
echo ""

echo -e "${BLUE}Recommendations for Small Droplets (512MB RAM):${NC}"
echo ""
echo "1. Monitor memory usage regularly:"
echo "   watch -n 5 free -h"
echo ""
echo "2. Monitor Docker container resources:"
echo "   docker stats"
echo ""
echo "3. If memory is consistently >90%, consider:"
echo "   - Upgrading to 1GB RAM droplet (\$6/month)"
echo "   - Reducing number of services"
echo "   - Adding swap space (not recommended for production)"
echo ""
echo "4. Run this optimization script weekly:"
echo "   ./deploy/optimize-droplet.sh"
echo ""
echo "5. Set up automated cleanup with cron:"
echo "   sudo crontab -e"
echo "   # Add: 0 2 * * 0 docker system prune -af"
echo ""

