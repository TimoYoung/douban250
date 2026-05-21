#!/bin/sh
set -e

# Create necessary directories
mkdir -p /app/data /app/posters

# Start the server (uv run uses the project venv automatically)
exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
