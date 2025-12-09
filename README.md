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

## 📋 Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) installed
- OpenAI API key
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))

## 🔧 Installation

### 1. Install uv (if not already installed)

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Clone and Setup

```bash
cd inventory_project

# Install dependencies with uv
uv sync

# Or install with dev dependencies
uv sync --all-extras
```

### 3. Configure Environment Variables

Edit the `.env` file with your credentials:

```bash
# OpenAI API Configuration
OPENAI_API_KEY=sk-...

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=123456789:ABC...

# Database Configuration
DATABASE_URL=sqlite:///./inventory.db

# Dashboard Configuration
DASHBOARD_PASSWORD=your_secure_password

# Application Configuration
APP_HOST=0.0.0.0
APP_PORT=8000
```

### 4. Get Your Telegram Bot Token

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` and follow the instructions
3. Copy the bot token to your `.env` file

## 🚀 Running the Application

### Start FastAPI Backend

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

### Set Telegram Webhook

Once FastAPI is running on a public URL (use ngrok for testing):

```bash
# Using ngrok for testing
ngrok http 8000

# Then set webhook
curl -X POST "http://localhost:8000/set-webhook?webhook_url=https://your-ngrok-url.ngrok.io/telegram-webhook"
```

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

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [uv Documentation](https://github.com/astral-sh/uv)

## 📄 License

MIT License

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
