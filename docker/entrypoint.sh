#!/bin/sh
set -e

# Create necessary directories
mkdir -p /app/data /app/posters

# Start the server using the pre-built venv
# python resolves to /opt/venv/bin/python via PATH
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
