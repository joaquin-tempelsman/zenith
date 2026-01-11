#!/bin/bash

# Digital Ocean Initial Setup Script
# Run this script on your Digital Ocean droplet to set up the environment

set -e

# Set non-interactive mode to avoid prompts
export DEBIAN_FRONTEND=noninteractive

echo "════════════════════════════════════════════════════════"
echo "  🌊 Digital Ocean Droplet Setup"
echo "════════════════════════════════════════════════════════"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Please run as root (use sudo)${NC}"
    exit 1
fi

echo -e "${BLUE}1️⃣  Updating system packages...${NC}"
apt-get update
# Use non-interactive upgrade with automatic config file handling
apt-get upgrade -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold"

echo ""
echo -e "${BLUE}2️⃣  Installing required packages...${NC}"
apt-get install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" \
    curl \
    git \
    ufw \
    fail2ban \
    ca-certificates \
    gnupg \
    lsb-release

echo ""
echo -e "${BLUE}3️⃣  Installing Docker...${NC}"
# Add Docker's official GPG key
mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
apt-get update
apt-get install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" \
    docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start and enable Docker
systemctl start docker
systemctl enable docker

echo ""
echo -e "${BLUE}4️⃣  Configuring firewall...${NC}"
# Configure UFW
ufw --force enable
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 8000/tcp  # FastAPI (optional, can be removed if using nginx)
ufw allow 8501/tcp  # Streamlit (optional, can be removed if using nginx)

echo ""
echo -e "${BLUE}5️⃣  Setting up application directory...${NC}"
mkdir -p /opt/inventory-system
cd /opt/inventory-system

echo ""
echo -e "${BLUE}6️⃣  Configuring fail2ban...${NC}"
systemctl start fail2ban
systemctl enable fail2ban

echo ""
echo -e "${BLUE}7️⃣  Creating deployment user...${NC}"
if ! id -u deploy > /dev/null 2>&1; then
    useradd -m -s /bin/bash deploy
    usermod -aG docker deploy
    echo -e "${GREEN}✅ User 'deploy' created${NC}"
else
    echo -e "${YELLOW}⚠️  User 'deploy' already exists${NC}"
fi

echo ""
echo "════════════════════════════════════════════════════════"
echo -e "${GREEN}✅ Digital Ocean Droplet Setup Complete!${NC}"
echo "════════════════════════════════════════════════════════"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo ""
echo "1. Clone your repository:"
echo "   cd /opt/inventory-system"
echo "   git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git ."
echo ""
echo "2. Create .env file:"
echo "   nano .env"
echo "   # Add your environment variables"
echo ""
echo "3. Start the application:"
echo "   docker compose -f docker-compose.prod.yml up -d"
echo ""
echo "4. Set up GitHub Actions secrets:"
echo "   DO_HOST: Your droplet IP address"
echo "   DO_USERNAME: deploy"
echo "   DO_SSH_KEY: Your SSH private key"
echo "   DO_APP_URL: https://your-domain.com"
echo ""
echo "5. Configure your domain DNS to point to this droplet"
echo ""
echo "6. Set up SSL certificates (Let's Encrypt recommended)"
echo ""

