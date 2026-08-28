# Stage 1: Build frontend
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --frozen-lockfile 2>/dev/null || npm install
COPY frontend/ .
RUN npm run build

# Stage 2: Python runtime
FROM python:3.12-slim
WORKDIR /app

# Install uv for fast dependency resolution
RUN pip install --no-cache-dir uv

# Copy dependency files first (layer caching)
COPY pyproject.toml uv.lock ./

# Install Python dependencies
RUN uv pip install --system --no-cache -e . 2>/dev/null || pip install --no-cache-dir .

# Copy application source
COPY src/ src/
COPY .env.example .env.example

# Copy built frontend from stage 1
COPY --from=frontend-build /app/frontend/dist frontend/dist

# Copy Atlas Guides (optional, for runtime reference)
COPY Atlas-Guides-V2.2/spec.md Atlas-Guides-V2.2/spec.md

# Set environment defaults for Railway
ENV PORT=8080
ENV HOST=0.0.0.0
ENV USE_LOCAL_SQLITE=1

# Expose port
EXPOSE 8080

# Run the application
CMD ["sh", "-c", "uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
