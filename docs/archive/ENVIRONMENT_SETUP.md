# Environment Setup Guide

## Overview

This project uses **two separate Telegram bots** to keep development and production environments completely isolated:

- **DEV Bot** (`TELEGRAM_BOT_TOKEN_DEV`) - For local development and testing
- **PROD Bot** (`TELEGRAM_BOT_TOKEN_PROD`) - For production on the droplet

The system automatically selects the correct bot based on the `ENVIRONMENT` variable.

## 🤖 Two-Bot Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DEVELOPMENT                              │
├─────────────────────────────────────────────────────────────┤
│  Telegram DEV Bot                                           │
│         ↓                                                   │
│  Local ngrok tunnel                                         │
│         ↓                                                   │
│  localhost:8000 (API)                                       │
│         ↓                                                   │
│  ./data/inventory.db (local database)                       │
│         ↓                                                   │
│  localhost:8501 (Dashboard)                                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    PRODUCTION                               │
├─────────────────────────────────────────────────────────────┤
│  Telegram PROD Bot                                          │
│         ↓                                                   │
│  Production ngrok tunnel                                    │
│         ↓                                                   │
│  159.203.139.96:8000 (API)                                  │
│         ↓                                                   │
│  /opt/inventory-system/data/inventory.db (prod database)    │
│         ↓                                                   │
│  159.203.139.96:8501 (Dashboard)                            │
└─────────────────────────────────────────────────────────────┘
```

## 📋 Prerequisites

### 1. Create Two Telegram Bots

You need to create two separate bots with [@BotFather](https://t.me/botfather):

**DEV Bot:**
```
/newbot
Name: Inventory System DEV
Username: your_inventory_dev_bot
```

**PROD Bot:**
```
/newbot
Name: Inventory System
Username: your_inventory_prod_bot
```

Save both bot tokens!

### 2. Configure Environment Variables

**Local `.env` file (on your computer):**
```env
# Set to development for local
ENVIRONMENT=development

# Both bot tokens (system will use DEV)
TELEGRAM_BOT_TOKEN_DEV=7970630255:AAHv9_TAsBwBPtZ5UIEozqHy9KOW5cdm-V8
TELEGRAM_BOT_TOKEN_PROD=8536410506:AAE6W5ZNQnpYsnQome4B6vQDGk6ei7JUDGM

# Other required vars
OPENAI_API_KEY=sk-proj-...
NGROK_AUTHTOKEN=...
DASHBOARD_PASSWORD=...
```

**Production `.env` file (on 159.203.139.96):**
```env
# Set to production for droplet
ENVIRONMENT=production

# Both bot tokens (system will use PROD)
TELEGRAM_BOT_TOKEN_DEV=7970630255:AAHv9_TAsBwBPtZ5UIEozqHy9KOW5cdm-V8
TELEGRAM_BOT_TOKEN_PROD=8536410506:AAE6W5ZNQnpYsnQome4B6vQDGk6ei7JUDGM

# Other required vars
OPENAI_API_KEY=sk-proj-...
NGROK_AUTHTOKEN=...
DASHBOARD_PASSWORD=...
```

## 🚀 Starting Development Environment

### Option 1: Using the Start Script (Recommended)

```bash
./start-dev.sh
```

This will:
- ✅ Set `ENVIRONMENT=development`
- ✅ Use `TELEGRAM_BOT_TOKEN_DEV`
- ✅ Start all services (API, Dashboard, ngrok)
- ✅ Configure webhook for DEV bot
- ✅ Show you all access URLs

### Option 2: Manual Start

```bash
export ENVIRONMENT=development
docker compose down
docker compose up -d
```

### Verify Development Setup

```bash
# Check which bot token is being used
curl http://localhost:8000/webhook-info

# Check inventory (should show local items)
curl http://localhost:8000/inventory

# Access dashboard
open http://localhost:8501
```

### Testing Development

1. **Send a message to your DEV bot**: "Add 5 bananas"
2. **Check local dashboard**: http://localhost:8501
3. **Verify item appears** in the local database

## 🌐 Deploying to Production

### Step 1: SSH into Droplet

```bash
ssh root@159.203.139.96
cd /opt/inventory-system
```

### Step 2: Ensure Production .env is Configured

```bash
# Check ENVIRONMENT is set to production
grep ENVIRONMENT .env

# Should show: ENVIRONMENT=production
```

### Step 3: Deploy

```bash
git pull origin main
./deploy/deploy-to-droplet.sh
```

This will:
- ✅ Set `ENVIRONMENT=production`
- ✅ Use `TELEGRAM_BOT_TOKEN_PROD`
- ✅ Start all services with production config
- ✅ Configure webhook for PROD bot
- ✅ Show deployment status

### Verify Production Setup

```bash
# Check which bot token is being used
curl http://159.203.139.96:8000/webhook-info

# Check inventory (production database)
curl http://159.203.139.96:8000/inventory

# Access dashboard
open http://159.203.139.96:8501
```

### Testing Production

1. **Send a message to your PROD bot**: "Add 10 oranges"
2. **Check production dashboard**: http://159.203.139.96:8501
3. **Verify item appears** in the production database

## 📊 Quick Reference

| Aspect | Development | Production |
|--------|-------------|------------|
| **Start Command** | `./start-dev.sh` | `./deploy/deploy-to-droplet.sh` |
| **ENVIRONMENT** | `development` | `production` |
| **Bot Token Used** | `TELEGRAM_BOT_TOKEN_DEV` | `TELEGRAM_BOT_TOKEN_PROD` |
| **Telegram Bot** | @your_inventory_dev_bot | @your_inventory_prod_bot |
| **Database** | `./data/inventory.db` | `/opt/.../data/inventory.db` |
| **Dashboard** | http://localhost:8501 | http://159.203.139.96:8501 |
| **API** | http://localhost:8000 | http://159.203.139.96:8000 |
| **ngrok** | Local tunnel | Production tunnel |

## 🔍 Troubleshooting

### Wrong Bot Receiving Messages

**Check which environment is active:**
```bash
# Local
curl http://localhost:8000/webhook-info

# Production
curl http://159.203.139.96:8000/webhook-info
```

The `url` field shows which ngrok tunnel is configured.

### Items Not Appearing in Dashboard

1. **Verify you're messaging the correct bot:**
   - DEV bot → Local dashboard
   - PROD bot → Production dashboard

2. **Check the database directly:**
   ```bash
   # Local
   curl http://localhost:8000/inventory
   
   # Production
   curl http://159.203.139.96:8000/inventory
   ```

3. **Restart the dashboard:**
   ```bash
   docker compose restart dashboard
   ```

### Environment Variable Not Set

If services start with wrong bot token:

```bash
# Local - ensure ENVIRONMENT is set
export ENVIRONMENT=development
docker compose down
docker compose up -d

# Production - check .env file
ssh root@159.203.139.96
cd /opt/inventory-system
grep ENVIRONMENT .env  # Should show: ENVIRONMENT=production
```

## 🎯 Best Practices

1. **Always use the start script** for local development: `./start-dev.sh`
2. **Keep both .env files in sync** (except ENVIRONMENT variable)
3. **Test locally first** before deploying to production
4. **Use DEV bot** for all testing and experimentation
5. **Use PROD bot** only for real inventory management
6. **Never mix environments** - keep data separate

## 📝 Summary

- ✅ Two separate Telegram bots (DEV and PROD)
- ✅ Automatic bot selection based on ENVIRONMENT variable
- ✅ Complete isolation between development and production
- ✅ Easy switching with start scripts
- ✅ No confusion about which database has data

