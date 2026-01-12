# ngrok Setup Guide - Two Tunnels for Dev & Prod

## 🚨 Problem

You currently have **ONE ngrok account** with **ONE static domain**: `juniper-subcritical-diurnally.ngrok-free.dev`

With the **free tier**, you can only have **ONE active tunnel** at a time using this domain.

**Current situation:**
- ❌ Local (DEV) and Production (PROD) **cannot run simultaneously**
- ❌ Whichever starts last kicks the other one offline
- ❌ Error: `ERR_NGROK_334 - endpoint is already online`

## ✅ Solutions

You have **3 options**:

---

## Option 1: Use Random URLs (Free - Recommended for Testing)

**Pros:**
- ✅ Completely free
- ✅ Both environments can run simultaneously
- ✅ No configuration needed

**Cons:**
- ⚠️ URL changes every time you restart
- ⚠️ Need to manually reconfigure Telegram webhook after each restart

### How to Implement

**For Production** - Remove the static domain from docker-compose.yml:

```bash
# On the droplet
ssh root@159.203.139.96
cd /opt/inventory-system
```

Edit `docker-compose.yml` and change the ngrok service:

```yaml
ngrok:
  image: ngrok/ngrok:latest
  container_name: inventory-ngrok
  restart: unless-stopped
  command:
    - "http"
    - "api:8000"
    # Remove the --domain line to get random URLs
  environment:
    - NGROK_AUTHTOKEN=${NGROK_AUTHTOKEN}
  ports:
    - "4040:4040"
  depends_on:
    api:
      condition: service_healthy
  networks:
    - inventory-network
```

Then restart:
```bash
docker compose down
docker compose up -d
```

**Result:**
- Local: `https://juniper-subcritical-diurnally.ngrok-free.dev` (static)
- Production: `https://random-name-12345.ngrok-free.app` (changes on restart)

---

## Option 2: Upgrade to ngrok Paid Plan (Recommended for Production)

**Cost:** $8/month (Personal plan) or $20/month (Pro plan)

**Benefits:**
- ✅ Multiple static domains
- ✅ Both environments run simultaneously
- ✅ Custom domains
- ✅ More bandwidth
- ✅ Better performance

### How to Upgrade

1. **Go to ngrok dashboard**: https://dashboard.ngrok.com/billing/subscription

2. **Choose a plan:**
   - **Personal ($8/month)**: 3 static domains, 3 agents
   - **Pro ($20/month)**: 5 static domains, 5 agents, custom domains

3. **Create a second static domain:**
   - Go to: https://dashboard.ngrok.com/cloud-edge/domains
   - Click "New Domain"
   - Choose a name like: `inventory-prod.ngrok-free.app`

4. **Update production docker-compose.yml:**

```yaml
ngrok:
  image: ngrok/ngrok:latest
  container_name: inventory-ngrok
  restart: unless-stopped
  command:
    - "http"
    - "api:8000"
    - "--domain=inventory-prod.ngrok-free.app"  # Your new domain
  environment:
    - NGROK_AUTHTOKEN=${NGROK_AUTHTOKEN}
  ports:
    - "4040:4040"
  depends_on:
    api:
      condition: service_healthy
  networks:
    - inventory-network
```

5. **Restart production:**
```bash
ssh root@159.203.139.96
cd /opt/inventory-system
docker compose down
docker compose up -d
```

**Result:**
- Local: `https://juniper-subcritical-diurnally.ngrok-free.dev`
- Production: `https://inventory-prod.ngrok-free.app`
- Both run simultaneously! ✅

---

## Option 3: Use Two Different ngrok Accounts (Free)

**Pros:**
- ✅ Completely free
- ✅ Both environments run simultaneously
- ✅ Each has a static domain

**Cons:**
- ⚠️ Need to manage two accounts
- ⚠️ Need two different auth tokens

### How to Implement

1. **Create a second ngrok account:**
   - Go to: https://ngrok.com/signup
   - Use a different email (e.g., Gmail + trick: `youremail+prod@gmail.com`)

2. **Get the new auth token:**
   - Login to the new account
   - Go to: https://dashboard.ngrok.com/get-started/your-authtoken
   - Copy the auth token

3. **Create a static domain for the new account:**
   - Go to: https://dashboard.ngrok.com/cloud-edge/domains
   - Click "Claim a free static domain"
   - You'll get something like: `another-random-name.ngrok-free.dev`

4. **Update production .env file:**

```bash
ssh root@159.203.139.96
cd /opt/inventory-system
nano .env
```

Change:
```env
# Use the NEW account's auth token
NGROK_AUTHTOKEN=<NEW_AUTH_TOKEN_HERE>
```

5. **Update production docker-compose.yml:**

```yaml
ngrok:
  image: ngrok/ngrok:latest
  container_name: inventory-ngrok
  restart: unless-stopped
  command:
    - "http"
    - "api:8000"
    - "--domain=another-random-name.ngrok-free.dev"  # New domain
  environment:
    - NGROK_AUTHTOKEN=${NGROK_AUTHTOKEN}
  ports:
    - "4040:4040"
  depends_on:
    api:
      condition: service_healthy
  networks:
    - inventory-network
```

6. **Restart production:**
```bash
docker compose down
docker compose up -d
```

**Result:**
- Local: `https://juniper-subcritical-diurnally.ngrok-free.dev` (Account 1)
- Production: `https://another-random-name.ngrok-free.dev` (Account 2)
- Both run simultaneously! ✅

---

## 📊 Comparison

| Option | Cost | Simultaneous | Static URLs | Complexity |
|--------|------|--------------|-------------|------------|
| **Random URLs** | Free | ✅ Yes | ⚠️ Local only | Easy |
| **Paid Plan** | $8-20/mo | ✅ Yes | ✅ Both | Easy |
| **Two Accounts** | Free | ✅ Yes | ✅ Both | Medium |

---

## 🎯 My Recommendation

**For now (testing):** Use **Option 1** (Random URLs for production)
- Quick to set up
- Free
- Good enough for testing

**For long-term (production):** Use **Option 2** (Paid plan)
- Professional setup
- Reliable static URLs
- Worth the $8/month for a production system

---

## 🚀 Quick Start - Option 1 (Random URLs)

Let me implement this for you right now:

```bash
# On production - remove static domain
ssh root@159.203.139.96
cd /opt/inventory-system
```

I'll update the docker-compose.yml to remove the static domain requirement.

---

## 📝 Next Steps

Which option would you like to use?

1. **Option 1** - I can implement it now (free, random prod URL)
2. **Option 2** - You upgrade ngrok, I'll configure it
3. **Option 3** - You create second account, I'll configure it

Let me know and I'll help you set it up!

