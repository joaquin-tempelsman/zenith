#!/bin/bash
#
# Daily Pipeline Runner
# This script activates the virtual environment and runs the Python pipeline
# Designed to be run by cron or manually
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "========================================"
echo "Daily Pipeline - $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}✗ Error: Virtual environment not found${NC}"
    echo "Please run setup.sh first"
    exit 1
fi

# Activate virtual environment
echo -e "${YELLOW}→ Activating virtual environment...${NC}"
source venv/bin/activate

# Check if Python script exists
if [ ! -f "generate_html.py" ]; then
    echo -e "${RED}✗ Error: generate_html.py not found${NC}"
    exit 1
fi

# Run the Python pipeline
echo -e "${YELLOW}→ Running Python pipeline...${NC}"
python3 generate_html.py

# Check exit status
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Pipeline completed successfully${NC}"
    echo "========================================"
    exit 0
else
    echo -e "${RED}✗ Pipeline failed${NC}"
    echo "========================================"
    exit 1
fi
