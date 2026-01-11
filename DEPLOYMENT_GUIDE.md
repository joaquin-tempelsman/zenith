# Deployment Guide

## Overview

This project supports two deployment modes:
- **Local Development**: Uses local database and ngrok tunnel
- **Production (Droplet)**: Uses production database on the server and ngrok tunnel

Both modes use ngrok to expose the API to Telegram for webhook functionality.

## Local Development

### Starting Local Development

```bash
# Start all services including ngrok
docker compose up -d

# This will start:
# - API (port 8000)
# - Dashboard (port 8501)
# - ngrok (port 4040 for web interface)
# - webhook-setup (runs once to configure Telegram)
```

### What Happens Locally

1. **Database**: `./data/inventory.db` (local file)
2. **ngrok**: Creates a public URL like `https://xxx.ngrok-free.dev`
3. **Telegram Webhook**: Automatically configured to point to ngrok URL
4. **Dashboard**: Access at `http://localhost:8501`

### Viewing ngrok Status

```bash
# View ngrok web interface
open http://localhost:4040

# Or check the public URL via API
curl http://localhost:4040/api/tunnels | python3 -m json.tool
```

## Production Deployment (Digital Ocean Droplet)

### Prerequisites

1. **Digital Ocean Droplet** with IP address (e.g., 159.203.139.96)
2. **SSH Access** configured
3. **.env file** on the droplet with production credentials

### Deploying to Droplet

#### Option 1: From the Droplet (Recommended)

```bash
# SSH into your droplet
ssh root@159.203.139.96

# Navigate to project directory
cd /opt/inventory-system

# Pull latest code
git pull origin main

# Run deployment script
./deploy/deploy-to-droplet.sh
```

#### Option 2: From Local Machine

```bash
# Use the setup script (first time only)
./deploy/setup-new-droplet.sh 159.203.139.96

# For subsequent deployments, SSH and run deploy script
ssh root@159.203.139.96 'cd /opt/inventory-system && git pull && ./deploy/deploy-to-droplet.sh'
```

### What Happens on Production

1. **Database**: `/opt/inventory-system/data/inventory.db` (on droplet)
2. **ngrok**: Creates a public URL for the droplet's API
3. **Telegram Webhook**: Automatically configured to point to ngrok URL
4. **Dashboard**: Access at `http://159.203.139.96:8501`
5. **API**: Access at `http://159.203.139.96:8000`

### Verifying Production Deployment

```bash
# Check service health
curl http://159.203.139.96:8000/health

# Check inventory items
curl http://159.203.139.96:8000/inventory

# View logs
ssh root@159.203.139.96 'cd /opt/inventory-system && docker compose logs -f'
```

## Key Differences

| Aspect | Local Development | Production (Droplet) |
|--------|------------------|---------------------|
| Database | `./data/inventory.db` | `/opt/inventory-system/data/inventory.db` |
| Dashboard URL | `http://localhost:8501` | `http://159.203.139.96:8501` |
| API URL | `http://localhost:8000` | `http://159.203.139.96:8000` |
| ngrok | Local tunnel | Droplet tunnel |
| Telegram Webhook | Points to local ngrok | Points to droplet ngrok |
| Code Changes | Hot-reload enabled | Requires rebuild |

## Environment Variables

Make sure your `.env` file contains:

```env
# Required for both local and production
OPENAI_API_KEY=sk-proj-...
TELEGRAM_BOT_TOKEN=...
NGROK_AUTHTOKEN=...
DASHBOARD_PASSWORD=...

# Optional
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=...
```

## Troubleshooting

### Telegram Bot Not Receiving Messages

1. Check ngrok is running:
   ```bash
   docker compose ps ngrok
   ```

2. Check webhook status:
   ```bash
   curl http://localhost:8000/webhook-info
   ```

3. Manually re-run webhook setup:
   ```bash
   docker compose run --rm webhook-setup
   ```

### Dashboard Shows No Items

1. Check which database you're looking at (local vs production)
2. Verify items exist in the database:
   ```bash
   curl http://localhost:8000/inventory  # Local
   curl http://159.203.139.96:8000/inventory  # Production
   ```

3. Restart dashboard:
   ```bash
   docker compose restart dashboard
   ```

### ngrok Tunnel Not Working

1. Verify NGROK_AUTHTOKEN is set in `.env`
2. Check ngrok logs:
   ```bash
   docker compose logs ngrok
   ```

3. Restart ngrok:
   ```bash
   docker compose restart ngrok
   docker compose run --rm webhook-setup
   ```

## Useful Commands

```bash
# View all running services
docker compose ps

# View logs for specific service
docker compose logs -f api
docker compose logs -f dashboard
docker compose logs -f ngrok

# Restart a service
docker compose restart api

# Stop all services
docker compose down

# Start fresh (removes volumes)
docker compose down -v
docker compose up -d
```

