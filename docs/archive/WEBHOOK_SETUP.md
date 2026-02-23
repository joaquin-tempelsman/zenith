# Telegram Webhook Setup Guide

This guide explains how the automatic webhook setup works in both development and production environments.

## Overview

The system automatically configures the Telegram webhook when you start the application:

- **Development**: Uses ngrok to create a public tunnel and sets the webhook automatically
- **Production**: Uses your public domain/IP and sets the webhook automatically

## Development Environment (with ngrok)

### Automatic Setup

When you start the development environment, the webhook is configured automatically:

```bash
# Using the interactive script
./docker-start.sh
# Select option 1: Development Environment

# Or using make
make dev

# Or using docker compose directly
docker compose --profile dev up -d
```

### What Happens Automatically

1. **API starts** - FastAPI application starts on port 8000
2. **ngrok starts** - Creates a public HTTPS tunnel to your local API
3. **Webhook setup runs** - Automatically:
   - Waits for ngrok to be ready
   - Gets the public ngrok URL
   - Sets the Telegram webhook to `https://your-ngrok-url.ngrok.io/telegram-webhook`
   - Displays the status

### Checking Webhook Status

```bash
# View webhook setup logs
docker logs inventory-webhook-setup

# Check current webhook info via API
curl http://localhost:8000/webhook-info

# View ngrok dashboard (shows all requests)
open http://localhost:4040
```

### ngrok Configuration (Optional)

For better ngrok experience, get a free authtoken:

1. Sign up at https://dashboard.ngrok.com/signup
2. Get your authtoken from https://dashboard.ngrok.com/get-started/your-authtoken
3. Add to your `.env` file:
   ```
   NGROK_AUTHTOKEN=your_token_here
   ```

Benefits of using an authtoken:
- Longer session times (no 2-hour limit)
- Custom domains (paid plans)
- More concurrent tunnels
- Better stability

### Manual Webhook Setup (Development)

If you need to manually set the webhook:

```bash
# Get the ngrok URL
curl http://localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url'

# Set the webhook manually
uv run python scripts/setup-webhook.py
```

## Production Environment (Digital Ocean / Cloud VM)

### Automatic Setup

When you deploy to production, the webhook is configured automatically:

```bash
# Deploy with docker compose
docker compose -f docker-compose.prod.yml up -d

# The webhook-setup service will automatically:
# 1. Wait for the API to be healthy
# 2. Get the public URL from environment variables
# 3. Set the Telegram webhook
```

### Configuration

Set your public URL in `.env`:

```bash
# Option 1: Using a domain name (recommended)
PUBLIC_URL=https://inventory.yourdomain.com
DOMAIN_NAME=inventory.yourdomain.com

# Option 2: Using an IP address
PUBLIC_URL=http://123.45.67.89:8000
```

### Checking Webhook Status

```bash
# View webhook setup logs
docker logs inventory-webhook-setup

# Check current webhook info via API
curl https://yourdomain.com/webhook-info
# or
curl http://your-ip:8000/webhook-info
```

### Manual Webhook Setup (Production)

If you need to manually set the webhook:

```bash
# Using the production script
PUBLIC_URL=https://yourdomain.com python scripts/setup-webhook-production.py

# Or using docker
docker compose -f docker-compose.prod.yml run --rm webhook-setup
```

## Troubleshooting

### Development Issues

**Problem**: Webhook setup fails with "Failed to get ngrok URL"

**Solution**:
```bash
# Check if ngrok is running
docker ps | grep ngrok

# Check ngrok logs
docker logs inventory-ngrok

# Restart ngrok
docker compose --profile dev restart ngrok
docker compose --profile dev restart webhook-setup
```

**Problem**: Telegram says "Webhook is already set"

**Solution**: This is normal! The webhook is working. You can verify:
```bash
curl http://localhost:8000/webhook-info
```

### Production Issues

**Problem**: Webhook setup fails with "Could not determine public URL"

**Solution**: Set the PUBLIC_URL environment variable:
```bash
# In your .env file
PUBLIC_URL=https://yourdomain.com

# Or when running
PUBLIC_URL=https://yourdomain.com docker compose -f docker-compose.prod.yml up -d
```

**Problem**: Telegram webhook returns SSL error

**Solution**: Make sure you're using HTTPS with a valid SSL certificate:
```bash
# Check if nginx is running with SSL
docker logs inventory-nginx

# Verify SSL certificate
curl -v https://yourdomain.com
```

## Webhook Endpoints

The application exposes these webhook-related endpoints:

- `POST /telegram-webhook` - Receives Telegram updates
- `GET /webhook-info` - Shows current webhook configuration
- `GET /health` - Health check endpoint

## Testing the Webhook

After setup, test your bot:

1. Send a message to your bot on Telegram
2. Check the API logs:
   ```bash
   docker logs -f inventory-api
   ```
3. You should see the webhook receiving and processing the message

## Stopping Services

### Development
```bash
# Stop all services including ngrok
docker compose --profile dev down

# This will stop:
# - API
# - Dashboard
# - ngrok
# - webhook-setup (already stopped after running once)
```

### Production
```bash
# Stop all services
docker compose -f docker-compose.prod.yml down
```

