#!/bin/bash

# Start Streamlit Dashboard

echo "🎨 Starting Streamlit Dashboard..."
echo ""
echo "Dashboard will be available at: http://localhost:8501"
echo ""

cd "$(dirname "$0")"
uv run streamlit run src/ui/dashboard.py
