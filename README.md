# Voice-Managed Inventory System

A full-stack inventory management system with voice input support via Telegram bot, powered by FastAPI, SQLite, and Streamlit.

## 🚀 Features

- 🎤 **Voice Input**: Send voice messages via Telegram for hands-free inventory management
- 💬 **Text Input**: Also supports text-based commands
- 🤖 **AI-Powered**: Uses OpenAI Whisper (STT) and GPT (intent parsing)
- 📊 **Dashboard**: Real-time inventory monitoring with Streamlit
- 💻 **SQL Runner**: Execute custom SQL queries directly from the UI
- 📅 **Expiration Tracking**: Track item expiration dates
- 🔔 **Smart Alerts**: Low stock and expiring items notifications
- 🐳 **Docker Support**: Fully containerized with Docker and Docker Compose
- 🔄 **CI/CD**: Automated testing and deployment with GitHub Actions
- ☁️ **Cloud Ready**: Easy deployment to Digital Ocean or any cloud VM

## 📁 Project Structure

```
inventory_project/
├── .env                    # Environment variables
├── .python-version         # Python version for uv
├── pyproject.toml          # Project dependencies (uv)
├── requirements.txt        # Legacy requirements (optional)
├── src/
│   ├── config.py           # Configuration management
│   ├── main.py             # FastAPI application
│   ├── database/
│   │   ├── models.py       # SQLAlchemy models
│   │   └── crud.py         # Database operations
│   ├── services/
│   │   ├── ai_processor.py # OpenAI integration
│   │   └── telegram.py     # Telegram Bot API
│   └── ui/
│       └── dashboard.py    # Streamlit dashboard
```

## 🛠️ Tech Stack

- **Backend**: FastAPI (Async Python web framework)
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: Streamlit
- **AI**: OpenAI API (Whisper + GPT-4)
- **Bot**: Telegram Bot API
- **Package Manager**: uv (fast Python package manager)
- **Containerization**: Docker & Docker Compose
- **CI/CD**: GitHub Actions
- **Reverse Proxy**: Nginx (production)

## 📋 Prerequisites

### For Docker (Recommended)
- Docker Desktop installed and running
- Git
- OpenAI API key
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))

### For Local Development (Alternative)
- Python 3.10+
- [uv](https://github.com/astral-sh/uv) installed
- OpenAI API key
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))

## 🔧 Quick Start

### Option 1: Docker (Recommended) 🐳

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

3. **Start with Docker**
   ```bash
   # Interactive setup (includes automatic ngrok + webhook setup)
   ./docker-start.sh

   # Or use Make
   make dev

   # Or manually with ngrok
   docker compose --profile dev up -d
   ```

4. **Access the application**
   - FastAPI: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Dashboard: http://localhost:8501
   - ngrok Dashboard: http://localhost:4040

   **Note**: The Telegram webhook is configured automatically! Just send a message to your bot to test it.

### Option 2: Local Development with uv

1. **Install uv**
   ```bash
   # macOS/Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Windows
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

2. **Clone and setup**
   ```bash
   git clone https://github.com/YOUR_USERNAME/inventory-system.git
   cd inventory-system

   # Install dependencies
   uv sync
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

4. **Run the application**
   ```bash
   # Start API
   ./start_api.sh

   # Start Dashboard (in another terminal)
   ./start_dashboard.sh
   ```

## 🔐 Environment Configuration

Get your Telegram Bot Token:
1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` and follow the instructions
3. Copy the bot token to your `.env` file

Required variables in `.env`:
```bash
OPENAI_API_KEY=sk-your-key-here
TELEGRAM_BOT_TOKEN=your-token-here
DASHBOARD_PASSWORD=your-secure-password

# Optional: ngrok authtoken for better development experience
NGROK_AUTHTOKEN=your-ngrok-token  # Get from https://dashboard.ngrok.com

# Optional: LangSmith tracing for debugging and monitoring
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your-langsmith-key  # Get from https://smith.langchain.com/settings
LANGSMITH_PROJECT=inventory-system
```

### 🔗 Telegram Webhook Setup

The webhook is **automatically configured** when you start the application:

**Development (with Docker)**:
- ngrok tunnel is created automatically
- Webhook is set to the ngrok URL automatically
- Just start the app and send a message to your bot!

**Production (Digital Ocean/Cloud)**:
- Set `PUBLIC_URL` in your `.env` file
- Webhook is configured automatically on startup
- Example: `PUBLIC_URL=https://yourdomain.com`

For detailed webhook setup information, see [docs/WEBHOOK_SETUP.md](docs/WEBHOOK_SETUP.md)

## 🚀 Running the Application

### With Docker

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

### Without Docker (Local Development)

#### Start FastAPI Backend

```bash
# Using uv
uv run python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Or navigate to src folder
cd src
uv run uvicorn main:app --reload
```

The API will be available at: `http://localhost:8000`

### Start Streamlit Dashboard

```bash
# Using uv (from project root)
uv run streamlit run src/ui/dashboard.py

# Or
cd src/ui
uv run streamlit run dashboard.py
```

The dashboard will be available at: `http://localhost:8501`

### Set Telegram Webhook (Manual - for local development without Docker)

If running locally without Docker, you'll need to set up ngrok manually:

```bash
# Start ngrok
ngrok http 8000

# In another terminal, run the webhook setup script
uv run python scripts/setup-webhook.py
```

**Note**: With Docker, this is done automatically! See [docs/WEBHOOK_SETUP.md](docs/WEBHOOK_SETUP.md) for details.

## 📱 Usage

### Telegram Bot Commands

Send voice or text messages to your bot:

#### Adding Items
- "Add 5 apples to fruits"
- "Add 10 bottles of milk to dairy, expires 2025-12-15"

#### Removing Items
- "Remove 3 bananas"
- "Take out 2 oranges"

#### Setting Quantity
- "Set milk to 10"
- "Update apple quantity to 20"

#### Checking Inventory
- "Check apple quantity"
- "How many bananas do we have?"

#### Deleting Items
- "Delete oranges"
- "Remove tomatoes completely"

### Dashboard Features

#### Inventory Tab
- View all items in a filterable table
- Category breakdown charts
- Low stock warnings
- Expiring items alerts
- Real-time statistics

#### SQL Runner Tab
- Execute custom SQL queries
- View results in table format
- Download results as CSV
- Example queries provided

## 🔐 Security

- Dashboard protected with password authentication
- Use environment variables for sensitive data
- Never commit `.env` file to version control

## 📊 Database Schema

### Items Table

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key, auto-increment |
| name | String | Item name |
| quantity | Integer | Current stock quantity |
| category | String | Item category |
| expire_date | Date | Expiration date (optional) |
| last_updated | DateTime | Last modification timestamp |

## 🧪 Development

### Install Dev Dependencies

```bash
uv sync --all-extras
```

### Run Tests

```bash
uv run pytest
```

### Code Formatting

```bash
# Format with black
uv run black src/

# Lint with ruff
uv run ruff check src/
```

## 📝 API Endpoints

### FastAPI Endpoints

- `GET /` - Health check and API info
- `GET /health` - System health status
- `POST /telegram-webhook` - Telegram webhook handler
- `GET /webhook-info` - Get webhook status
- `POST /set-webhook` - Set webhook URL
- `GET /inventory` - Get all inventory items
- `GET /inventory/summary` - Get inventory statistics

### API Documentation

Once FastAPI is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🐛 Troubleshooting

### Database Not Found
```bash
# Initialize database manually
uv run python -c "from src.database.models import init_db; init_db()"
```

### Telegram Webhook Not Working
- Ensure your FastAPI server is publicly accessible (use ngrok for testing)
- Verify webhook URL is HTTPS
- Check webhook status: `GET /webhook-info`

### OpenAI API Errors
- Verify API key is correct in `.env`
- Check OpenAI account has credits
- Ensure you have access to Whisper and GPT models

## 🚢 Deployment

### Deploy to Digital Ocean

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete deployment instructions.

**Quick deployment:**

1. **Create a Digital Ocean droplet**
   - Ubuntu 22.04 LTS
   - Minimum $6/month plan

2. **Run setup script on droplet**
   ```bash
   curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/inventory-system/main/deploy/digital-ocean-setup.sh | sudo bash
   ```

3. **Clone and configure**
   ```bash
   cd /opt/inventory-system
   git clone https://github.com/YOUR_USERNAME/inventory-system.git .
   cp .env.example .env
   # Edit .env with production credentials
   # IMPORTANT: Set PUBLIC_URL for automatic webhook setup
   # Example: PUBLIC_URL=https://yourdomain.com
   ```

4. **Deploy**
   ```bash
   docker compose -f docker-compose.prod.yml up -d
   ```

   The Telegram webhook will be configured automatically! Check the setup logs:
   ```bash
   docker logs inventory-webhook-setup
   ```

### CI/CD with GitHub Actions

This project includes automated CI/CD pipelines:

- **CI Pipeline** (`.github/workflows/ci.yml`): Runs tests and builds on every push
- **CD Pipeline** (`.github/workflows/cd.yml`): Deploys to production on push to `main`

**Setup GitHub Secrets:**
- `DO_HOST`: Your droplet IP
- `DO_USERNAME`: SSH username
- `DO_SSH_KEY`: SSH private key
- `DO_APP_URL`: Your application URL
- `OPENAI_API_KEY`: For tests

### Docker Commands

```bash
# Development
make dev              # Start development environment
make logs             # View logs
make down             # Stop services

# Production
make prod             # Start production environment
make deploy           # Deploy to production
make prod-logs        # View production logs

# Utilities
make health           # Check application health
make db-backup        # Backup database
make clean            # Clean up containers and volumes
```

## 📚 Additional Resources

- [DEPLOYMENT.md](DEPLOYMENT.md) - Complete deployment guide
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [uv Documentation](https://github.com/astral-sh/uv)
- [Docker Documentation](https://docs.docker.com/)

## 📄 License

MIT License

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
