# Stage 1: Build frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci || npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend
FROM python:3.12-slim
WORKDIR /app

# Install uv
RUN pip install uv

# Copy backend dependencies
COPY backend/pyproject.toml ./
RUN uv pip install --system -e ".[mysql,postgres]" 2>/dev/null || uv pip install --system -e .

# Copy backend code
COPY backend/ ./

# Copy frontend build output
COPY --from=frontend-build /app/frontend/dist ./static

# Create directories
RUN mkdir -p data posters

# Copy entrypoint
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
