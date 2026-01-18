# 🚀 Deployment Guide

Complete guide for deploying the Voice-Managed Inventory System using Docker and GitHub Actions.

## 📋 Table of Contents

- [Local Development](#local-development)
- [Digital Ocean Deployment](#digital-ocean-deployment)
- [GitHub Actions CI/CD](#github-actions-cicd)
- [Environment Variables](#environment-variables)
- [SSL/HTTPS Setup](#sslhttps-setup)
- [Troubleshooting](#troubleshooting)

---

## 🏠 Local Development

### Prerequisites

- Docker Desktop installed and running
- Git
- `.env` file with your credentials

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/inventory-system.git
   cd inventory-system
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

3. **Start with Docker Compose**
   ```bash
   # Build and start all services
   docker compose up -d
   
   # View logs
   docker compose logs -f
   ```

4. **Access the application**
   - FastAPI: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Dashboard: http://localhost:8501
   - Health Check: http://localhost:8000/health

### Development Commands

```bash
# Stop services
docker compose down

# Rebuild and restart
docker compose up -d --build

# View specific service logs
docker compose logs -f api
docker compose logs -f dashboard

# Execute commands in container
docker compose exec api python -c "from src.database.models import init_db; init_db()"

# Clean up everything
docker compose down -v
docker system prune -af
```

---

## 🌊 Digital Ocean Deployment

### Step 1: Create a Droplet

1. Log in to [Digital Ocean](https://www.digitalocean.com/)
2. Create a new Droplet:
   - **Image**: Ubuntu 22.04 LTS
   - **Plan**: Basic ($6/month minimum recommended)
   - **Datacenter**: Choose closest to your users
   - **Authentication**: SSH keys (recommended)
   - **Hostname**: inventory-system

### Step 2: Initial Server Setup

1. **SSH into your droplet**
   ```bash
   ssh root@YOUR_DROPLET_IP
   ```

2. **Run the setup script**
   ```bash
   # Download and run the setup script
   curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/inventory-system/main/deploy/digital-ocean-setup.sh -o setup.sh
   chmod +x setup.sh
   sudo ./setup.sh
   ```

   Or manually:
   ```bash
   # Update system
   apt-get update && apt-get upgrade -y
   
   # Install Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh
   
   # Install Docker Compose
   apt-get install docker-compose-plugin -y
   
   # Configure firewall
   ufw allow ssh
   ufw allow 80/tcp
   ufw allow 443/tcp
   ufw --force enable
   ```

### Step 3: Deploy the Application

1. **Clone your repository**
   ```bash
   mkdir -p /opt/inventory-system
   cd /opt/inventory-system
   git clone https://github.com/YOUR_USERNAME/inventory-system.git .
   ```

2. **Create production .env file**
   ```bash
   nano .env
   ```
   
   Add your production credentials:
   ```env
   OPENAI_API_KEY=sk-your-production-key
   TELEGRAM_BOT_TOKEN=your-production-token
   DASHBOARD_PASSWORD=secure-production-password
   GITHUB_REPOSITORY=your-username/inventory-system
   ```

3. **Start the application**
   ```bash
   docker compose -f docker-compose.prod.yml up -d
   ```

4. **Verify deployment**
   ```bash
   # Check service status
   docker compose -f docker-compose.prod.yml ps
   
   # Check health
   curl http://localhost:8000/health
   ```

### Step 4: Configure Domain (Optional)

1. **Point your domain to the droplet**
   - Add an A record pointing to your droplet's IP

2. **Update nginx configuration**
   ```bash
   nano nginx/nginx.conf
   # Update server_name with your domain
   ```

---

## 🔄 GitHub Actions CI/CD

### Setup GitHub Secrets

Go to your repository → Settings → Secrets and variables → Actions

Add the following secrets:

| Secret Name | Description | Example |
|------------|-------------|---------|
| `DO_HOST` | Droplet IP address | `123.45.67.89` |
| `DO_USERNAME` | SSH username | `root` or `deploy` |
| `DO_SSH_KEY` | Private SSH key | Contents of `~/.ssh/id_rsa` |
| `DO_SSH_PORT` | SSH port (optional) | `22` |
| `DO_APP_URL` | Application URL | `http://123.45.67.89:8000` |
| `OPENAI_API_KEY` | OpenAI API key (for tests) | `sk-...` |

### Workflows

#### CI Workflow (`.github/workflows/ci.yml`)
- Triggers on: Push to `main`/`develop`, Pull Requests
- Actions:
  - Runs tests
  - Linting and type checking
  - Builds Docker image
  - Validates image

#### CD Workflow (`.github/workflows/cd.yml`)
- Triggers on: Push to `main`, Manual dispatch
- Actions:
  - Builds and pushes Docker image to GitHub Container Registry
  - Deploys to Digital Ocean via SSH
  - Verifies deployment health

### Manual Deployment

Trigger manual deployment from GitHub:
1. Go to Actions tab
2. Select "CD - Deploy to Production"
3. Click "Run workflow"
4. Select branch and run

---

## 🔐 Environment Variables

### Required Variables

| Variable | Description | Where to Get |
|----------|-------------|--------------|
| `OPENAI_API_KEY` | OpenAI API key for Whisper & GPT | https://platform.openai.com/api-keys |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | https://t.me/botfather |
| `DASHBOARD_PASSWORD` | Password for dashboard access | Choose a secure password |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key | - |
| `DATABASE_URL` | Database connection string | `sqlite:///./data/inventory.db` |
| `APP_HOST` | FastAPI host | `0.0.0.0` |
| `APP_PORT` | FastAPI port | `8000` |
| `GITHUB_REPOSITORY` | GitHub repo for container registry | `username/repo` |

---

## 🔒 SSL/HTTPS Setup

### Option 1: Let's Encrypt (Recommended)

1. **Install Certbot**
   ```bash
   apt-get install certbot python3-certbot-nginx -y
   ```

2. **Obtain SSL certificate**
   ```bash
   certbot --nginx -d your-domain.com -d www.your-domain.com
   ```

3. **Auto-renewal**
   ```bash
   # Test renewal
   certbot renew --dry-run

   # Certbot automatically sets up a cron job
   ```

### Option 2: Manual SSL Certificates

1. **Place certificates in nginx/ssl/**
   ```bash
   mkdir -p nginx/ssl
   cp your-cert.pem nginx/ssl/cert.pem
   cp your-key.pem nginx/ssl/key.pem
   ```

2. **Update nginx configuration**
   - Certificates are already configured in `nginx/nginx.conf`

3. **Restart nginx**
   ```bash
   docker compose -f docker-compose.prod.yml restart nginx
   ```

---

## 🐛 Troubleshooting

### Services won't start

```bash
# Check logs
docker compose logs -f

# Check specific service
docker compose logs api
docker compose logs dashboard

# Verify environment variables
docker compose config
```

### Database issues

```bash
# Initialize database manually
docker compose exec api python -c "from src.database.models import init_db; init_db()"

# Check database file
docker compose exec api ls -la /app/data/
```

### Port conflicts

```bash
# Check what's using the port
lsof -i :8000
lsof -i :8501

# Kill the process or change ports in docker-compose.yml
```

### GitHub Actions deployment fails

1. **Verify secrets are set correctly**
   - Check repository Settings → Secrets

2. **Test SSH connection**
   ```bash
   ssh -i ~/.ssh/id_rsa user@YOUR_DROPLET_IP
   ```

3. **Check droplet logs**
   ```bash
   ssh root@YOUR_DROPLET_IP
   cd /opt/inventory-system
   docker compose -f docker-compose.prod.yml logs
   ```

### Telegram webhook not working

1. **Set webhook URL**
   ```bash
   curl -X POST "http://YOUR_DOMAIN/set-webhook?webhook_url=https://YOUR_DOMAIN/telegram-webhook"
   ```

2. **Check webhook status**
   ```bash
   curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"
   ```

### Health check fails

```bash
# Check API health
curl http://localhost:8000/health

# Check from outside
curl http://YOUR_DROPLET_IP:8000/health

# Check Docker health
docker ps
```

---

## 📊 Monitoring

### View Logs

```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Specific service
docker compose -f docker-compose.prod.yml logs -f api

# Last 100 lines
docker compose -f docker-compose.prod.yml logs --tail=100
```

### Check Resource Usage

```bash
# Container stats
docker stats

# Disk usage
docker system df

# Clean up
docker system prune -af
```

### Backup Database

```bash
# Backup
docker compose exec api cp /app/data/inventory.db /app/data/inventory.db.backup

# Copy to host
docker cp inventory-api:/app/data/inventory.db ./backup-$(date +%Y%m%d).db

# Restore
docker cp backup-20231225.db inventory-api:/app/data/inventory.db
docker compose restart api
```

---

## 🔄 Updates and Maintenance

### Update Application

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker compose -f docker-compose.prod.yml up -d --build

# Or use the deployment script
./deploy/deploy-prod.sh
```

### Update Dependencies

```bash
# Update pyproject.toml
# Then rebuild
docker compose -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.prod.yml up -d
```

---

## 📞 Support

For issues and questions:
- Check the [README.md](README.md) for general information
- Review logs: `docker compose logs -f`
- Check GitHub Issues
- Verify environment variables are set correctly

---

## 🎯 Quick Reference

### Local Development
```bash
docker compose up -d                    # Start
docker compose logs -f                  # View logs
docker compose down                     # Stop
```

### Production Deployment
```bash
docker compose -f docker-compose.prod.yml up -d     # Start
docker compose -f docker-compose.prod.yml logs -f   # View logs
docker compose -f docker-compose.prod.yml down      # Stop
```

### Useful URLs
- Local API: http://localhost:8000
- Local Dashboard: http://localhost:8501
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health



