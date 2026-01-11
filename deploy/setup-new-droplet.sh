#!/bin/bash

# ════════════════════════════════════════════════════════
#  🚀 Complete DigitalOcean Droplet Setup Script
# ════════════════════════════════════════════════════════
#
# This script automates the entire droplet setup process
# Run this from your LOCAL machine after creating a new droplet
#
# Usage: ./deploy/setup-new-droplet.sh <DROPLET_IP>
#

set -euo pipefail

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Configuration
DROPLET_IP="$1"
SSH_KEY_PATH="$HOME/.ssh/docean"
REPO_NAME="joaquin-tempelsman/zenith"
APP_DIR="/opt/inventory-system"

# ════════════════════════════════════════════════════════
# Helper Functions
# ════════════════════════════════════════════════════════

print_header() {
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}$1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_step() {
    echo -e "${YELLOW}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

wait_for_user() {
    echo ""
    echo -e "${YELLOW}${BOLD}⏸  HUMAN INPUT REQUIRED${NC}"
    echo -e "${YELLOW}$1${NC}"
    echo ""
    read -p "Press ENTER when ready to continue..."
    echo ""
}

run_on_droplet() {
    ssh -o StrictHostKeyChecking=no -i "$SSH_KEY_PATH" root@"$DROPLET_IP" "$@"
}

# ════════════════════════════════════════════════════════
# Validation
# ════════════════════════════════════════════════════════

if [ -z "$DROPLET_IP" ]; then
    print_error "Usage: $0 <DROPLET_IP>"
    echo "Example: $0 159.203.139.96"
    exit 1
fi

print_header "🌊 DigitalOcean Droplet Setup"
echo "Droplet IP: $DROPLET_IP"
echo "Repository: $REPO_NAME"
echo "App Directory: $APP_DIR"
echo ""

# ════════════════════════════════════════════════════════
# STEP 1: SSH Key Setup
# ════════════════════════════════════════════════════════

print_header "STEP 1: SSH Key Setup"

if [ ! -f "$SSH_KEY_PATH" ]; then
    print_step "Creating SSH key for droplet access..."
    ssh-keygen -t ed25519 -f "$SSH_KEY_PATH" -C "docean-server" -N ""
    print_success "SSH key created at $SSH_KEY_PATH"
    
    echo ""
    echo -e "${BOLD}Public Key:${NC}"
    cat "${SSH_KEY_PATH}.pub"
    echo ""
    
    wait_for_user "1. Open DigitalOcean console for your droplet\n2. Run: echo \"$(cat ${SSH_KEY_PATH}.pub)\" >> ~/.ssh/authorized_keys"
else
    print_success "SSH key already exists at $SSH_KEY_PATH"
fi

# ════════════════════════════════════════════════════════
# STEP 2: Update SSH Config
# ════════════════════════════════════════════════════════

print_header "STEP 2: Update SSH Config"

print_step "Removing old SSH host key if exists..."
ssh-keygen -R "$DROPLET_IP" 2>/dev/null || true
print_success "Old host key removed"

print_step "Updating ~/.ssh/config..."

# Remove old docean entry if exists
sed -i.bak '/^Host docean$/,/^$/d' ~/.ssh/config 2>/dev/null || true

# Add new entry
cat >> ~/.ssh/config << EOF

Host docean
  Hostname $DROPLET_IP
  User root
  IdentityFile $SSH_KEY_PATH
  AddKeysToAgent yes
  UseKeychain yes
EOF

print_success "SSH config updated"

# ════════════════════════════════════════════════════════
# STEP 3: Test SSH Connection
# ════════════════════════════════════════════════════════

print_header "STEP 3: Test SSH Connection"

print_step "Testing SSH connection..."
if run_on_droplet "echo 'SSH connection successful'"; then
    print_success "SSH connection working"
else
    print_error "SSH connection failed"
    exit 1
fi

# ════════════════════════════════════════════════════════
# STEP 4: Run Initial Droplet Setup
# ════════════════════════════════════════════════════════

print_header "STEP 4: Initial Droplet Setup"

print_step "Copying setup script to droplet..."
scp -i "$SSH_KEY_PATH" deploy/digital-ocean-setup.sh root@"$DROPLET_IP":/tmp/
print_success "Setup script copied"

print_step "Running setup script (this will take 3-5 minutes)..."
printf "${YELLOW}Installing Docker, configuring firewall, setting up fail2ban...${NC}\n"
run_on_droplet "sudo bash /tmp/digital-ocean-setup.sh"
print_success "Droplet setup complete"

# ════════════════════════════════════════════════════════
# STEP 5: Create GitHub Deploy Key
# ════════════════════════════════════════════════════════

print_header "STEP 5: GitHub Deploy Key"

print_step "Creating GitHub deploy key on droplet..."
DEPLOY_KEY=$(run_on_droplet "ssh-keygen -t ed25519 -f ~/.ssh/github_deploy -C 'zenith-deploy' -N '' >/dev/null 2>&1 && cat ~/.ssh/github_deploy.pub")
print_success "Deploy key created"

echo ""
echo -e "${BOLD}GitHub Deploy Key:${NC}"
echo "$DEPLOY_KEY"
echo ""

wait_for_user "1. Go to: https://github.com/$REPO_NAME/settings/keys\n2. Click 'Add deploy key'\n3. Title: 'DigitalOcean Droplet - $(date +%Y-%m-%d)'\n4. Paste the key above\n5. ✅ Check 'Allow write access'\n6. Click 'Add key'"

# ════════════════════════════════════════════════════════
# STEP 6: Configure SSH for GitHub
# ════════════════════════════════════════════════════════

print_header "STEP 6: Configure SSH for GitHub"

print_step "Setting up SSH config for GitHub on droplet..."
run_on_droplet "cat >> ~/.ssh/config << 'EOF'
Host github.com
  Hostname github.com
  IdentityFile ~/.ssh/github_deploy
  AddKeysToAgent yes
EOF"
print_success "SSH config updated for GitHub"

# ════════════════════════════════════════════════════════
# STEP 7: Clone Repository
# ════════════════════════════════════════════════════════

print_header "STEP 7: Clone Repository"

print_step "Cloning repository to $APP_DIR..."
run_on_droplet "cd $APP_DIR && git init && git remote add origin git@github.com:$REPO_NAME.git && GIT_SSH_COMMAND='ssh -o StrictHostKeyChecking=no' git pull origin main"
print_success "Repository cloned"

# ════════════════════════════════════════════════════════
# STEP 8: Copy .env File
# ════════════════════════════════════════════════════════

print_header "STEP 8: Copy Environment File"

if [ ! -f ".env" ]; then
    print_error ".env file not found in current directory"
    wait_for_user "Please create a .env file in the current directory with your production settings"
fi

print_step "Copying .env file to droplet..."
scp -i "$SSH_KEY_PATH" .env root@"$DROPLET_IP":"$APP_DIR"/.env
print_success ".env file copied"

# ════════════════════════════════════════════════════════
# STEP 9: Setup Data Directory
# ════════════════════════════════════════════════════════

print_header "STEP 9: Setup Data Directory"

print_step "Creating data directory with proper permissions..."
run_on_droplet "cd $APP_DIR && mkdir -p data && chmod 777 data"
print_success "Data directory created"

# ════════════════════════════════════════════════════════
# STEP 10: Build Docker Images
# ════════════════════════════════════════════════════════

print_header "STEP 10: Build Docker Images"

print_step "Building Docker images (this will take 3-5 minutes)..."
printf "${YELLOW}Building api and dashboard images...${NC}\n"
run_on_droplet "cd $APP_DIR && docker compose build"
print_success "Docker images built"

# ════════════════════════════════════════════════════════
# STEP 11: Clean Up Build Cache
# ════════════════════════════════════════════════════════

print_header "STEP 11: Clean Up Build Cache"

print_step "Cleaning up Docker build cache to free disk space..."
run_on_droplet "cd $APP_DIR && docker builder prune -af && docker system prune -f" >/dev/null 2>&1
print_success "Build cache cleaned"

# ════════════════════════════════════════════════════════
# STEP 12: Start Services
# ════════════════════════════════════════════════════════

print_header "STEP 12: Start Services"

print_step "Starting Docker containers..."
run_on_droplet "cd $APP_DIR && docker compose up -d api dashboard"
print_success "Containers started"

print_step "Waiting for services to start (30 seconds)..."
sleep 30
print_success "Services should be ready"

# ════════════════════════════════════════════════════════
# STEP 13: Verify Deployment
# ════════════════════════════════════════════════════════

print_header "STEP 13: Verify Deployment"

# Check container status
print_step "Checking container status..."
CONTAINER_STATUS=$(run_on_droplet "cd $APP_DIR && docker compose ps --format json" 2>/dev/null || echo "[]")

# Check API health
print_step "Testing API health endpoint..."
API_HEALTH=$(run_on_droplet "curl -s http://localhost:8000/health" 2>/dev/null || echo "{}")

# Parse results
API_RUNNING=$(echo "$CONTAINER_STATUS" | grep -q "inventory-api" && echo "true" || echo "false")
DASHBOARD_RUNNING=$(echo "$CONTAINER_STATUS" | grep -q "inventory-dashboard" && echo "true" || echo "false")
API_HEALTHY=$(echo "$API_HEALTH" | grep -q "healthy" && echo "true" || echo "false")
DB_CONNECTED=$(echo "$API_HEALTH" | grep -q "connected" && echo "true" || echo "false")

# ════════════════════════════════════════════════════════
# FINAL SUMMARY
# ════════════════════════════════════════════════════════

print_header "🎉 DEPLOYMENT SUMMARY"

echo -e "${BOLD}Droplet Information:${NC}"
echo "  IP Address: $DROPLET_IP"
echo "  SSH Alias: docean"
echo ""

echo -e "${BOLD}Service Status:${NC}"
if [ "$API_RUNNING" = "true" ]; then
    print_success "API Container: Running"
else
    print_error "API Container: Not Running"
fi

if [ "$DASHBOARD_RUNNING" = "true" ]; then
    print_success "Dashboard Container: Running"
else
    print_error "Dashboard Container: Not Running"
fi

echo ""
echo -e "${BOLD}Health Checks:${NC}"
if [ "$API_HEALTHY" = "true" ]; then
    print_success "API Health: Healthy"
else
    print_error "API Health: Unhealthy"
fi

if [ "$DB_CONNECTED" = "true" ]; then
    print_success "Database: Connected"
else
    print_error "Database: Not Connected"
fi

echo ""
echo -e "${BOLD}Access URLs:${NC}"
echo "  API:       http://$DROPLET_IP:8000"
echo "  API Docs:  http://$DROPLET_IP:8000/docs"
echo "  Dashboard: http://$DROPLET_IP:8501"

echo ""
echo -e "${BOLD}Next Steps:${NC}"
echo "  1. Update GitHub Secret DO_APP_URL to: http://$DROPLET_IP:8000"
echo "  2. Test the API: curl http://$DROPLET_IP:8000/health"
echo "  3. Open dashboard in browser: http://$DROPLET_IP:8501"

echo ""
echo -e "${BOLD}Useful Commands:${NC}"
echo "  Connect to droplet:    ssh docean"
echo "  View logs:             ssh docean 'cd $APP_DIR && docker compose logs -f'"
echo "  Restart services:      ssh docean 'cd $APP_DIR && docker compose restart'"
echo "  Stop services:         ssh docean 'cd $APP_DIR && docker compose down'"

echo ""

# Overall status
if [ "$API_RUNNING" = "true" ] && [ "$DASHBOARD_RUNNING" = "true" ] && [ "$API_HEALTHY" = "true" ] && [ "$DB_CONNECTED" = "true" ]; then
    print_header "✅ DEPLOYMENT SUCCESSFUL!"
    echo -e "${GREEN}All services are running and healthy!${NC}"
    echo ""
    exit 0
else
    print_header "⚠️  DEPLOYMENT COMPLETED WITH WARNINGS"
    echo -e "${YELLOW}Some services may need attention. Check the status above.${NC}"
    echo ""
    echo "To troubleshoot, run:"
    echo "  ssh docean 'cd $APP_DIR && docker compose logs'"
    echo ""
    exit 1
fi

