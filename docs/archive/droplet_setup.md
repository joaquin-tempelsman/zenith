# DigitalOcean Droplet Setup Guide

**Repository:** `joaquin-tempelsman/zenith`

This guide assumes you're setting up a new droplet for the same repository.

---

## 🚀 Quick Setup (Automated)

**Use this automated script for the fastest setup:**

```bash
./deploy/setup-new-droplet.sh <DROPLET_IP>
```

**Example:**
```bash
./deploy/setup-new-droplet.sh 159.203.139.96
```

The script will:
- ✅ Configure SSH keys and access
- ✅ Install Docker and dependencies
- ✅ Set up firewall and security
- ✅ Create GitHub deploy key (with prompts)
- ✅ Clone repository
- ✅ Build and start services
- ✅ Verify deployment
- ✅ Show comprehensive status summary

**Human input required for:**
1. Adding SSH public key to droplet (if first time)
2. Adding GitHub deploy key to repository settings

---

## Prerequisites

- [ ] New DigitalOcean droplet created (Ubuntu 24.04 recommended)
- [ ] Droplet IP address noted
- [ ] `.env` file in your local repository root

---

## Manual Setup (Step-by-Step)

If you prefer manual setup or need to troubleshoot, follow these steps:

---

## Step 1: Create SSH Key for Droplet Access

On your **local machine**:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/docean -C "docean-server"
```

**Copy the public key:**
```bash
cat ~/.ssh/docean.pub
```

**Add to droplet:**
- Use DigitalOcean console (Access → Launch Droplet Console)
- Run: `echo "YOUR_PUBLIC_KEY_HERE" >> ~/.ssh/authorized_keys`

**Test connection:**
```bash
ssh -i ~/.ssh/docean root@YOUR_DROPLET_IP
```

---

## Step 2: Add SSH Config Entry (Optional but Recommended)

On your **local machine**, add to `~/.ssh/config`:

```
Host docean
  Hostname YOUR_DROPLET_IP
  User root
  IdentityFile ~/.ssh/docean
  AddKeysToAgent yes
  UseKeychain yes
```

Now you can connect with: `ssh docean`

---

## Step 3: Run Initial Droplet Setup

On your **local machine**:

```bash
# Copy setup script to droplet
scp deploy/digital-ocean-setup.sh docean:/tmp/

# Run setup script
ssh docean "sudo bash /tmp/digital-ocean-setup.sh"
```

This installs Docker, configures firewall, and sets up the environment.

---

## Step 4: Create GitHub Deploy Key

On the **droplet** (via SSH):

```bash
ssh-keygen -t ed25519 -f ~/.ssh/github_deploy -C 'zenith-deploy' -N ''
cat ~/.ssh/github_deploy.pub
```

**Copy the output** and add it to GitHub:
1. Go to: https://github.com/joaquin-tempelsman/zenith/settings/keys
2. Click **"Add deploy key"**
3. Title: `DigitalOcean Droplet - [DATE or IDENTIFIER]`
4. Paste the public key
5. ✅ **Check "Allow write access"**
6. Click **"Add key"**

---

## Step 5: Configure SSH for GitHub on Droplet

On the **droplet**:

```bash
cat >> ~/.ssh/config << 'EOF'
Host github.com
  Hostname github.com
  IdentityFile ~/.ssh/github_deploy
  AddKeysToAgent yes
EOF
```

---

## Step 6: Clone Repository

On the **droplet**:

```bash
cd /opt/inventory-system
git init
git remote add origin git@github.com:joaquin-tempelsman/zenith.git
GIT_SSH_COMMAND='ssh -o StrictHostKeyChecking=no' git pull origin main
```

---

## Step 7: Create .env File

On your **local machine**:

```bash
# Copy your local .env to the droplet
scp .env docean:/opt/inventory-system/.env
```

**OR** manually create it on the droplet with your production values.

---

## Step 8: Deploy Application

On the **droplet**:

```bash
cd /opt/inventory-system

# Create data directory with proper permissions
mkdir -p data
chmod 777 data

# Build images
docker compose build

# Clean up build cache to free disk space (important for small droplets)
docker builder prune -af
docker system prune -f

# Start services
docker compose up -d api dashboard

# Wait for services to start (about 30 seconds)
sleep 30

# Check status
docker compose ps
docker compose logs api --tail=20
```

---

## Step 9: Verify Deployment

On the **droplet**:

```bash
# Check service status
docker compose -f docker-compose.prod.yml ps

# Check logs
docker compose -f docker-compose.prod.yml logs -f

# Test health endpoint
curl http://localhost:8000/health
```

**Access from browser:**
- API: `http://YOUR_DROPLET_IP:8000`
- API Docs: `http://YOUR_DROPLET_IP:8000/docs`
- Dashboard: `http://YOUR_DROPLET_IP:8501`

---

## Step 10: Configure GitHub Actions (Optional - for CI/CD)

Add these secrets to your GitHub repository:
- Go to: Repository → Settings → Secrets and variables → Actions

**Required secrets:**
- `DO_HOST`: Your droplet IP address
- `DO_USERNAME`: `root` (or `deploy` if using that user)
- `DO_SSH_KEY`: Contents of `~/.ssh/docean` (private key)
- `DO_SSH_PORT`: `22`
- `DO_APP_URL`: `http://YOUR_DROPLET_IP:8000`

Now every push to `main` will automatically deploy!

---

## Quick Reference Commands

```bash
# View logs
docker compose -f docker-compose.prod.yml logs -f

# Restart services
docker compose -f docker-compose.prod.yml restart

# Stop services
docker compose -f docker-compose.prod.yml down

# Update and redeploy
cd /opt/inventory-system
git pull origin main
docker compose -f docker-compose.prod.yml up -d --build

# Clean up old images
docker image prune -af
```

---

## Troubleshooting

**Can't connect via SSH:**
- Check firewall allows SSH: `ufw status`
- Verify SSH key is correct

**Docker not found:**
- Re-run setup script: `sudo bash /tmp/digital-ocean-setup.sh`

**Services not starting:**
- Check logs: `docker compose -f docker-compose.prod.yml logs`
- Verify .env file exists and has correct values
- Check disk space: `df -h`

**Port not accessible:**
- Check firewall: `ufw status`
- Allow port: `sudo ufw allow 8000/tcp`

