# Deployment Scripts

This directory contains automated deployment scripts for the Zenith inventory system.

## 🚀 Quick Start - New Droplet Setup

### Automated Setup (Recommended)

```bash
./deploy/setup-new-droplet.sh <DROPLET_IP>
```

**Example:**
```bash
./deploy/setup-new-droplet.sh 159.203.139.96
```

### What It Does

The script automates the entire droplet setup process:

1. **SSH Key Setup** - Creates and configures SSH keys for droplet access
2. **SSH Config Update** - Updates `~/.ssh/config` with new droplet IP
3. **Initial Droplet Setup** - Installs Docker, configures firewall, sets up fail2ban
4. **GitHub Deploy Key** - Creates SSH key for GitHub repository access
5. **Repository Clone** - Clones the repository to `/opt/inventory-system`
6. **Environment Setup** - Copies `.env` file to droplet
7. **Docker Build** - Builds application images
8. **Service Start** - Starts API and Dashboard containers
9. **Verification** - Tests all services and shows comprehensive status

### Human Input Required

The script will pause and wait for you at these points:

1. **SSH Key Addition** (if first time)
   - You'll need to add the SSH public key to your droplet via DigitalOcean console

2. **GitHub Deploy Key**
   - You'll need to add the deploy key to your GitHub repository settings
   - URL: https://github.com/joaquin-tempelsman/zenith/settings/keys

### Prerequisites

- New DigitalOcean droplet created (Ubuntu 24.04 recommended)
- `.env` file in your local repository root
- GitHub repository access

### Output

The script provides:
- ✅ Real-time progress updates
- ✅ Clear status indicators
- ✅ Comprehensive deployment summary
- ✅ Service health checks
- ✅ Access URLs
- ✅ Next steps and useful commands

### Example Output

```
════════════════════════════════════════════════════════
🎉 DEPLOYMENT SUMMARY
════════════════════════════════════════════════════════

Droplet Information:
  IP Address: 159.203.139.96
  SSH Alias: docean

Service Status:
✅ API Container: Running
✅ Dashboard Container: Running

Health Checks:
✅ API Health: Healthy
✅ Database: Connected

Access URLs:
  API:       http://159.203.139.96:8000
  API Docs:  http://159.203.139.96:8000/docs
  Dashboard: http://159.203.139.96:8501
```

---

## 📁 Files in This Directory

### `setup-new-droplet.sh`
Complete automated setup script for new droplets. Run this from your local machine.

### `digital-ocean-setup.sh`
Server-side setup script that runs on the droplet. Installs Docker, configures firewall, etc.
This is called automatically by `setup-new-droplet.sh`.

---

## 🔧 Troubleshooting

### Script fails at SSH connection
- Ensure your droplet is running
- Check that you've added the SSH public key to the droplet
- Verify the IP address is correct

### GitHub clone fails
- Ensure you've added the deploy key to GitHub
- Check that "Allow write access" is enabled on the deploy key

### Services not starting
- Check logs: `ssh docean 'cd /opt/inventory-system && docker compose logs'`
- Verify `.env` file has correct values
- Check disk space: `ssh docean 'df -h'`

### Health check fails
- Wait an additional 30 seconds and check again
- View API logs: `ssh docean 'cd /opt/inventory-system && docker compose logs api'`
- Verify database connection in `.env`

---

## 📝 Manual Commands

If you need to run steps manually:

```bash
# Connect to droplet
ssh docean

# View logs
ssh docean 'cd /opt/inventory-system && docker compose logs -f'

# Restart services
ssh docean 'cd /opt/inventory-system && docker compose restart'

# Rebuild and restart
ssh docean 'cd /opt/inventory-system && docker compose up -d --build'

# Check status
ssh docean 'cd /opt/inventory-system && docker compose ps'

# Test health
curl http://YOUR_DROPLET_IP:8000/health
```

---

## 🔄 Updating Existing Droplet

To update code on an existing droplet:

```bash
ssh docean 'cd /opt/inventory-system && git pull origin main && docker compose up -d --build'
```

Or use GitHub Actions for automatic deployment on push to main.

