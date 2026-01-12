# Quick Start Guide

## 🚀 Start Development (Local)

```bash
./start-dev.sh
```

**What happens:**
- Uses **DEV Telegram bot**
- Local database at `./data/inventory.db`
- Dashboard at http://localhost:8501
- API at http://localhost:8000

**Test it:**
1. Send message to your **DEV bot**: "Add 5 apples"
2. Open http://localhost:8501
3. See the item appear!

---

## 🌐 Deploy to Production (Droplet)

```bash
ssh root@159.203.139.96
cd /opt/inventory-system
git pull origin main
./deploy/deploy-to-droplet.sh
```

**What happens:**
- Uses **PROD Telegram bot**
- Production database at `/opt/inventory-system/data/inventory.db`
- Dashboard at http://159.203.139.96:8501
- API at http://159.203.139.96:8000

**Test it:**
1. Send message to your **PROD bot**: "Add 10 oranges"
2. Open http://159.203.139.96:8501
3. See the item appear!

---

## 🔑 Key Differences

| | Development | Production |
|---|---|---|
| **Command** | `./start-dev.sh` | `./deploy/deploy-to-droplet.sh` |
| **Bot** | DEV bot | PROD bot |
| **Dashboard** | localhost:8501 | 159.203.139.96:8501 |
| **Database** | Local | Droplet |

---

## ⚠️ Important

- **DEV bot** messages → Local database
- **PROD bot** messages → Production database
- They are **completely separate**!

---

## 🆘 Troubleshooting

**Items not showing up?**
```bash
# Check which bot is configured
curl http://localhost:8000/webhook-info        # Local
curl http://159.203.139.96:8000/webhook-info   # Production

# Check database
curl http://localhost:8000/inventory            # Local
curl http://159.203.139.96:8000/inventory       # Production
```

**Wrong environment?**
```bash
# Restart with correct environment
./start-dev.sh                                  # For local
./deploy/deploy-to-droplet.sh                   # For production
```

---

## 📚 More Info

See [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md) for detailed documentation.

