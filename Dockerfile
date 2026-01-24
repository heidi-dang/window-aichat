# Multi-stage Dockerfile for Window AI Chat
# Stage 1: Build Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/webapp

# Copy package files
COPY webapp/package*.json ./
RUN npm ci --no-audit --no-fund

# Copy source code
COPY webapp/ ./

# Build with increased memory
ENV NODE_OPTIONS="--max-old-space-size=4096"
# Set backend URL for build time if needed (though usually it's runtime for SPA)
ARG VITE_BACKEND_URL
ENV VITE_BACKEND_URL=${VITE_BACKEND_URL}
RUN npm run build

# Stage 2: Runtime (Python + Static Files)
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY window_aichat/ ./window_aichat/

# Copy frontend build artifacts
COPY --from=frontend-builder /app/webapp/dist /app/static

# Create necessary directories
RUN mkdir -p server_cache/repo_cache workspace

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the server
CMD ["python", "-m", "window_aichat", "server", "--host", "0.0.0.0", "--port", "8000"]
