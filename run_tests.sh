#!/bin/bash
cd "$(dirname "$0")"
uv run pytest tests/test_agent_e2e.py -v --tb=short 2>&1 | tee /tmp/zenith_e2e_results.txt
echo "EXIT_CODE=$?" >> /tmp/zenith_e2e_results.txt

