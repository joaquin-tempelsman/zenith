# 🚀 Deployment Instructions

## ✅ Setup Complete!

Your inventory system now supports **two separate environments** with **two separate Telegram bots**:

- **DEV Environment** (Local) - For testing and development
- **PROD Environment** (Droplet) - For real inventory management

---

## 📱 Your Telegram Bots

| Environment | Bot Token | Bot Name |
|-------------|-----------|----------|
| **DEV** | `7970630255:AAHv9...` | Your DEV bot |
| **PROD** | `8536410506:AAE6W...` | Your PROD bot |

---

## 🖥️ Starting Development Environment (Local)

### Quick Start

```bash
./start-dev.sh
```

### What This Does

1. ✅ Sets `ENVIRONMENT=development`
2. ✅ Uses `TELEGRAM_BOT_TOKEN_DEV` (7970630255...)
3. ✅ Starts all services (API, Dashboard, ngrok)
4. ✅ Configures Telegram webhook for DEV bot
5. ✅ Shows all access URLs

### Access Your Local Environment

- **Dashboard**: http://localhost:8501
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **ngrok Web UI**: http://localhost:4040

### Test It

1. Send a message to your **DEV Telegram bot**: "Add 5 apples"
2. Open http://localhost:8501
3. See the item appear in your local dashboard!

---

## 🌐 Deploying to Production (Droplet)

### Step 1: SSH into Your Droplet

```bash
ssh root@159.203.139.96
```

### Step 2: Navigate to Project Directory

```bash
cd /opt/inventory-system
```

### Step 3: Pull Latest Changes

```bash
git pull origin main
```

### Step 4: Deploy

```bash
./deploy/deploy-to-droplet.sh
```

### What This Does

1. ✅ Sets `ENVIRONMENT=production`
2. ✅ Uses `TELEGRAM_BOT_TOKEN_PROD` (8536410506...)
3. ✅ Starts all services with production config
4. ✅ Configures Telegram webhook for PROD bot
5. ✅ Shows deployment status

### Access Your Production Environment

- **Dashboard**: http://159.203.139.96:8501
- **API**: http://159.203.139.96:8000
- **API Docs**: http://159.203.139.96:8000/docs

### Test It

1. Send a message to your **PROD Telegram bot**: "Add 10 oranges"
2. Open http://159.203.139.96:8501
3. See the item appear in your production dashboard!

---

## 🔑 Key Differences

| Aspect | Development | Production |
|--------|-------------|------------|
| **Start Command** | `./start-dev.sh` | `./deploy/deploy-to-droplet.sh` |
| **Location** | Your computer | Droplet (159.203.139.96) |
| **ENVIRONMENT** | `development` | `production` |
| **Bot Token** | `TELEGRAM_BOT_TOKEN_DEV` | `TELEGRAM_BOT_TOKEN_PROD` |
| **Bot ID** | 7970630255 | 8536410506 |
| **Database** | `./data/inventory.db` | `/opt/.../data/inventory.db` |
| **Dashboard** | localhost:8501 | 159.203.139.96:8501 |
| **Purpose** | Testing & Development | Real Inventory |

---

## 🎯 Important Notes

### Complete Isolation

- **DEV bot messages** → Local database only
- **PROD bot messages** → Production database only
- The two environments are **completely separate**
- You can run both at the same time!

### Which Bot to Use?

- **Testing new features?** → Use DEV bot
- **Experimenting?** → Use DEV bot
- **Managing real inventory?** → Use PROD bot

### Workflow

1. **Develop locally** using DEV bot
2. **Test thoroughly** on your local machine
3. **Deploy to production** when ready
4. **Use PROD bot** for real inventory management

---

## 🔍 Verification Commands

### Check Which Environment is Running

**Local:**
```bash
docker compose exec api python3 -c "from src.config import settings; print('Environment:', settings.environment)"
```

**Production:**
```bash
ssh root@159.203.139.96 'cd /opt/inventory-system && docker compose exec api python3 -c "from src.config import settings; print(\"Environment:\", settings.environment)"'
```

### Check Which Bot is Configured

**Local:**
```bash
curl http://localhost:8000/webhook-info | python3 -m json.tool
```

**Production:**
```bash
curl http://159.203.139.96:8000/webhook-info | python3 -m json.tool
```

### Check Database Contents

**Local:**
```bash
curl http://localhost:8000/inventory | python3 -m json.tool
```

**Production:**
```bash
curl http://159.203.139.96:8000/inventory | python3 -m json.tool
```

---

## 🆘 Troubleshooting

### Items Not Appearing?

1. **Verify you're messaging the correct bot:**
   - DEV bot (7970630255) → Local dashboard
   - PROD bot (8536410506) → Production dashboard

2. **Check the webhook configuration:**
   ```bash
   curl http://localhost:8000/webhook-info  # Local
   curl http://159.203.139.96:8000/webhook-info  # Production
   ```

3. **Restart the services:**
   ```bash
   ./start-dev.sh  # Local
   ./deploy/deploy-to-droplet.sh  # Production
   ```

### Wrong Environment?

If the wrong bot token is being used, restart with the correct script:

```bash
# For local development
./start-dev.sh

# For production (on droplet)
./deploy/deploy-to-droplet.sh
```

---

## 📚 Additional Documentation

- **[ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md)** - Detailed environment configuration guide
- **[QUICK_START.md](QUICK_START.md)** - Quick reference card
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Full deployment guide

---

## ✨ Summary

You now have a **professional two-environment setup**:

✅ Separate DEV and PROD Telegram bots  
✅ Automatic environment detection  
✅ Complete data isolation  
✅ Easy deployment scripts  
✅ No confusion about which database has data  

**Happy coding! 🎉**

