#!/bin/bash

# Setup Verification Script
# Checks if all requirements are met for running the application

set -e

echo "════════════════════════════════════════════════════════"
echo "  🔍 Setup Verification"
echo "════════════════════════════════════════════════════════"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

# Function to check command
check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "${GREEN}✅${NC} $1 is installed"
        return 0
    else
        echo -e "${RED}❌${NC} $1 is NOT installed"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

# Function to check file
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✅${NC} $1 exists"
        return 0
    else
        echo -e "${YELLOW}⚠️${NC}  $1 not found"
        WARNINGS=$((WARNINGS + 1))
        return 1
    fi
}

# Function to check directory
check_directory() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✅${NC} $1 exists"
        return 0
    else
        echo -e "${YELLOW}⚠️${NC}  $1 not found"
        WARNINGS=$((WARNINGS + 1))
        return 1
    fi
}

echo -e "${BLUE}Checking required tools...${NC}"
echo ""

# Check Docker
if check_command docker; then
    if docker info > /dev/null 2>&1; then
        echo -e "${GREEN}✅${NC} Docker is running"
    else
        echo -e "${RED}❌${NC} Docker is installed but not running"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check Docker Compose
check_command "docker compose" || check_command "docker-compose"

# Check Git
check_command git

# Check uv (optional for local development)
if check_command uv; then
    echo -e "${BLUE}   (uv is optional when using Docker)${NC}"
fi

echo ""
echo -e "${BLUE}Checking project files...${NC}"
echo ""

# Check essential files
check_file "Dockerfile"
check_file "infrastructure/docker-compose.yml"
check_file "infrastructure/docker-compose.prod.yml"
check_file "pyproject.toml"
check_file ".dockerignore"
check_file "Makefile"

echo ""
echo -e "${BLUE}Checking configuration files...${NC}"
echo ""

# Check .env
if check_file ".env"; then
    # Check if .env has required variables
    if grep -q "OPENAI_API_KEY=" .env && grep -q "TELEGRAM_BOT_TOKEN=" .env; then
        echo -e "${GREEN}✅${NC} .env has required variables"
    else
        echo -e "${YELLOW}⚠️${NC}  .env is missing required variables"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo -e "${YELLOW}   Create .env from .env.example${NC}"
fi

check_file ".env.example"

echo ""
echo -e "${BLUE}Checking deployment files...${NC}"
echo ""

check_directory "deploy"
check_file "deploy/digital-ocean-setup.sh"
check_file "deploy/deploy-prod.sh"

echo ""
echo -e "${BLUE}Checking GitHub Actions...${NC}"
echo ""

check_directory ".github/workflows"
check_file ".github/workflows/ci.yml"
check_file ".github/workflows/cd.yml"

echo ""
echo -e "${BLUE}Checking Nginx configuration...${NC}"
echo ""

check_directory "infrastructure"
check_file "infrastructure/nginx.conf"

if ! check_directory "infrastructure/ssl"; then
    echo -e "${BLUE}   (SSL directory will be created when needed)${NC}"
fi

echo ""
echo "════════════════════════════════════════════════════════"

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
    echo "════════════════════════════════════════════════════════"
    echo ""
    echo -e "${BLUE}You're ready to start!${NC}"
    echo ""
    echo "Quick start options:"
    echo "  1. Using Docker:     scripts/docker-start.sh"
    echo "  2. Using Make:       make dev"
    echo "  3. Manual:           docker compose up -d"
    echo ""
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠️  Setup complete with ${WARNINGS} warning(s)${NC}"
    echo "════════════════════════════════════════════════════════"
    echo ""
    echo "You can proceed, but review the warnings above."
    echo ""
else
    echo -e "${RED}❌ Setup incomplete: ${ERRORS} error(s), ${WARNINGS} warning(s)${NC}"
    echo "════════════════════════════════════════════════════════"
    echo ""
    echo "Please fix the errors above before proceeding."
    echo ""
    exit 1
fi

