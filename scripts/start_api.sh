#!/bin/bash

# Start FastAPI Backend

echo "🚀 Starting FastAPI Backend..."
echo ""
echo "API will be available at: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""

cd "$(dirname "$0")"
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
