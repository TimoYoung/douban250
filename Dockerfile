# Stage 1: Build frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci || npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Build Python dependencies + install Playwright browser
FROM python:3.12-slim-bookworm AS deps-build
WORKDIR /build

# Install uv for fast dependency installation
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY backend/pyproject.toml backend/uv.lock ./

# Verify lockfile consistency with pyproject.toml (fail fast on mismatch)
RUN uv lock --check

# Create a virtual environment and install dependencies + Playwright Chromium
ENV VIRTUAL_ENV=/opt/venv
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright
RUN uv venv /opt/venv && \
    uv export --no-dev --frozen | uv pip install --python /opt/venv/bin/python -r /dev/stdin && \
    uv run playwright install chromium && \
    # 清理构建缓存（最佳努力，不掩盖关键错误）
    find /opt/venv -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null && \
    find /opt/venv -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete 2>/dev/null && \
    rm -rf /root/.local

# Stage 3: Final runtime image
FROM python:3.12-slim-bookworm
WORKDIR /app

# Copy venv and Playwright browser from builder
COPY --from=deps-build /opt/venv /opt/venv
COPY --from=deps-build /opt/playwright /opt/playwright
ENV PATH="/opt/venv/bin:$PATH"
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright

# Copy backend application code
COPY backend/app ./app
COPY backend/pyproject.toml ./pyproject.toml

# Copy frontend build output
COPY --from=frontend-build /app/backend/static ./static

# System runtime deps (Chromium needs these) + cleanup
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libdbus-1-3 libxkbcommon0 libatspi2.0-0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 \
    libcairo2 libasound2 libwayland-client0 fonts-liberation \
    && rm -rf /var/lib/apt/lists/* \
    # 移除 pip/setuptools/test 模块节省 ~25MB
    && rm -rf /usr/local/lib/python3.12/site-packages/pip \
              /usr/local/lib/python3.12/site-packages/pip-* \
              /usr/local/lib/python3.12/site-packages/setuptools \
              /usr/local/lib/python3.12/site-packages/setuptools-* \
              /usr/local/lib/python3.12/ensurepip \
              /usr/local/bin/pip* \
    && find /usr/local/lib/python3.12 -type d \( -name 'test' -o -name 'tests' -o -name 'idle_test' \) -prune -exec rm -rf {} + 2>/dev/null \
    && find /usr/local/lib/python3.12 -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null \
    && mkdir -p data posters

# Copy entrypoint
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
