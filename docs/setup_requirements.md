# Setup Requirements

Quick reference for setting up the Zenith inventory management system.

## Prerequisites

- Docker Desktop installed
- OpenAI API key
- Telegram Bot Token (from @BotFather)
- ngrok authtoken (optional, recommended)

## 1. Get API Keys

### OpenAI API Key
1. Go to https://platform.openai.com/api-keys
2. Create new secret key
3. Copy the key

### Telegram Bot Token
1. Open Telegram, search for @BotFather
2. Send `/newbot`
3. Follow prompts to name your bot
4. Copy the token provided

**For two-bot setup (recommended):**
- Create one bot for development (e.g., `MyInventoryDevBot`)
- Create another for production (e.g., `MyInventoryBot`)

### ngrok Authtoken (Optional)
1. Go to https://dashboard.ngrok.com/signup
2. Sign up/login
3. Copy authtoken from dashboard

## 2. Configure Environment

```bash
# Clone the repository
git clone <repo-url>
cd zenith

# Create environment file
cp .env.example .env
```

Edit `.env` with your values:

```env
# Required
OPENAI_API_KEY=sk-...
TELEGRAM_BOT_TOKEN_DEV=123456:ABC...   # For local development
TELEGRAM_BOT_TOKEN_PROD=789012:XYZ...  # For production
DASHBOARD_PASSWORD=your-secure-password

# Optional
NGROK_AUTHTOKEN=your-ngrok-token
ENVIRONMENT=development

# Optional: LangSmith tracing
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your-key
LANGSMITH_PROJECT=zenith
```

## 3. Verify Setup

```bash
# Check Docker is running
docker --version

# Verify .env file exists
cat .env
```

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for LLM |
| `TELEGRAM_BOT_TOKEN_DEV` | Yes | Dev bot token |
| `TELEGRAM_BOT_TOKEN_PROD` | Yes | Prod bot token |
| `DASHBOARD_PASSWORD` | Yes | Dashboard access password |
| `NGROK_AUTHTOKEN` | No | For stable webhook tunnels |
| `ENVIRONMENT` | No | `development` or `production` |
