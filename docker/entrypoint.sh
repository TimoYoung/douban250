#!/bin/sh
set -e

# Create necessary directories
mkdir -p /app/data /app/posters

# Start the server
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
