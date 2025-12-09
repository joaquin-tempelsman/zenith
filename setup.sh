#!/bin/bash

# Voice-Managed Inventory System - Startup Script

echo "🚀 Starting Voice-Managed Inventory System..."
echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Please install it first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "✅ uv is installed"

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
uv sync

# Check .env file
if [ ! -f .env ]; then
    echo ""
    echo "⚠️  Warning: .env file not found!"
    echo "   Please create .env file with your configuration."
    exit 1
fi

echo ""
echo "✅ Configuration loaded"

# Initialize database
echo ""
echo "🗄️  Initializing database..."
uv run python -c "from src.database.models import init_db; init_db(); print('✅ Database initialized')"

echo ""
echo "════════════════════════════════════════════════════════"
echo "  Voice-Managed Inventory System"
echo "════════════════════════════════════════════════════════"
echo ""
echo "To start the services, run:"
echo ""
echo "  FastAPI Backend:"
echo "    uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "  Streamlit Dashboard:"
echo "    uv run streamlit run src/ui/dashboard.py"
echo ""
echo "  API Docs: http://localhost:8000/docs"
echo "  Dashboard: http://localhost:8501"
echo ""
echo "════════════════════════════════════════════════════════"
