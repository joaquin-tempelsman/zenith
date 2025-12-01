#!/bin/bash
#
# Setup Script for Daily Pipeline
# Run this script once on your DigitalOcean droplet to set everything up
#
# Usage: sudo ./setup.sh
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "========================================"
echo "  Daily Pipeline Setup"
echo "========================================"
echo -e "${NC}"

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}✗ Please run with sudo: sudo ./setup.sh${NC}"
    exit 1
fi

# Get the actual user (not root if using sudo)
ACTUAL_USER=${SUDO_USER:-$USER}
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo -e "${YELLOW}→ Step 1: Updating system packages...${NC}"
apt update && apt upgrade -y

echo -e "${YELLOW}→ Step 2: Installing required packages...${NC}"
apt install -y python3 python3-pip python3-venv nginx git

echo -e "${YELLOW}→ Step 3: Setting up Python virtual environment...${NC}"
cd "$SCRIPT_DIR"
if [ -d "venv" ]; then
    echo "  Virtual environment already exists, skipping..."
else
    sudo -u "$ACTUAL_USER" python3 -m venv venv
    echo -e "${GREEN}  ✓ Virtual environment created${NC}"
fi

echo -e "${YELLOW}→ Step 4: Installing Python dependencies...${NC}"
sudo -u "$ACTUAL_USER" bash -c "source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt"
echo -e "${GREEN}  ✓ Dependencies installed${NC}"

echo -e "${YELLOW}→ Step 5: Creating web directory...${NC}"
mkdir -p /var/www/daily-pipeline
chown -R "$ACTUAL_USER:$ACTUAL_USER" /var/www/daily-pipeline
echo -e "${GREEN}  ✓ Web directory created at /var/www/daily-pipeline${NC}"

echo -e "${YELLOW}→ Step 6: Configuring Nginx...${NC}"
# Remove default site and any backups
rm -f /etc/nginx/sites-enabled/default
rm -f /etc/nginx/sites-enabled/default.backup
echo "  Removed default Nginx sites"

# Copy our Nginx config
cp "$SCRIPT_DIR/nginx.conf" /etc/nginx/sites-available/daily-pipeline
ln -sf /etc/nginx/sites-available/daily-pipeline /etc/nginx/sites-enabled/daily-pipeline

# Test Nginx configuration
nginx -t
if [ $? -eq 0 ]; then
    systemctl restart nginx
    systemctl enable nginx
    echo -e "${GREEN}  ✓ Nginx configured and restarted${NC}"
else
    echo -e "${RED}  ✗ Nginx configuration test failed${NC}"
    exit 1
fi

echo -e "${YELLOW}→ Step 7: Configuring firewall (UFW)...${NC}"
ufw allow 'Nginx Full'
ufw allow OpenSSH
echo "y" | ufw enable
ufw status verbose
echo -e "${GREEN}  ✓ Firewall configured${NC}"

echo -e "${YELLOW}→ Step 8: Making scripts executable...${NC}"
chmod +x "$SCRIPT_DIR/run_pipeline.sh"
chown "$ACTUAL_USER:$ACTUAL_USER" "$SCRIPT_DIR/run_pipeline.sh"
echo -e "${GREEN}  ✓ Scripts are executable${NC}"

echo -e "${YELLOW}→ Step 9: Running initial pipeline...${NC}"
sudo -u "$ACTUAL_USER" "$SCRIPT_DIR/run_pipeline.sh"

echo -e "${YELLOW}→ Step 10: Setting up cron job...${NC}"
CRON_CMD="* * * * * $SCRIPT_DIR/run_pipeline.sh >> /var/log/daily-pipeline.log 2>&1"

# Determine which user to set cron for
if [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
    CRON_USER="$SUDO_USER"
else
    CRON_USER="root"
fi

# Add cron job for the appropriate user
(crontab -u "$CRON_USER" -l 2>/dev/null | grep -v "run_pipeline.sh"; echo "$CRON_CMD") | crontab -u "$CRON_USER" -

# Create log file with proper permissions
touch /var/log/daily-pipeline.log
chown "$CRON_USER:$CRON_USER" /var/log/daily-pipeline.log

echo -e "${GREEN}  ✓ Cron job scheduled for user: $CRON_USER (every minute)${NC}"
echo -e "${YELLOW}  Run 'crontab -l' as $CRON_USER to verify${NC}"

echo ""
echo -e "${BLUE}========================================"
echo "  Setup Complete! 🎉"
echo "========================================${NC}"
echo ""
echo -e "${GREEN}Your pipeline is now running!${NC}"
echo ""
echo "Access your site:"
echo "  → http://$(hostname -I | awk '{print $1}')"
echo "  → http://[$(hostname -I | awk '{print $2}')]  (IPv6)"
echo ""
echo "Useful commands:"
echo "  • Manual run:    ./run_pipeline.sh"
echo "  • View logs:     tail -f /var/log/daily-pipeline.log"
echo "  • Check cron:    crontab -l"
echo "  • Nginx status:  systemctl status nginx"
echo "  • Firewall:      sudo ufw status"
echo ""
echo -e "${YELLOW}Note: Cron job will run every minute${NC}"
echo -e "${YELLOW}To change schedule, edit with: crontab -e${NC}"
echo ""
