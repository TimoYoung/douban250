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

# System dependencies for Playwright/Chromium — single layer, minimal set
# 保留 liberation 字体（网页渲染需要），去掉 emoji 字体（爬虫不需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libdbus-1-3 libxkbcommon0 libatspi2.0-0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 \
    libcairo2 libasound2 libwayland-client0 fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Install uv with no cache
RUN pip install --no-cache-dir uv

# Copy dependency files first for layer caching
COPY backend/pyproject.toml backend/uv.lock ./

# Install Python dependencies (locked, no dev)
RUN uv sync --no-dev --frozen

# Install Playwright Chromium only (system deps already installed above)
RUN uv run playwright install chromium

# Copy backend application code only (tests/scripts excluded)
COPY backend/app ./app
COPY backend/pyproject.toml ./pyproject.toml

# Copy frontend build output
COPY --from=frontend-build /app/backend/static ./static

# Create directories
RUN mkdir -p data posters

# Copy entrypoint
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
