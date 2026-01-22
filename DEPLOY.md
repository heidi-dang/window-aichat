# Docker Deployment Guide

## Quick Start

### 1. Build and Run Locally

```bash
# Build and start all services
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### 2. Production Deployment

#### Option A: Using Pre-built Images from GitHub Container Registry

```bash
# Pull latest images
docker-compose -f docker-compose.prod.yml pull

# Start services
docker-compose -f docker-compose.prod.yml up -d
```

#### Option B: Build Locally on Server

```bash
# Clone repo
git clone https://github.com/heidi-dang/window-aichat.git
cd window-aichat

# Build and start
docker-compose up -d --build
```

## Environment Variables

Create a `.env` file (optional):

```env
# Backend
PYTHONUNBUFFERED=1

# Frontend
VITE_API_BASE=http://localhost:8000
```

## Volumes

The following directories are persisted:
- `./server_cache` - Backend cache and repo data
- `./workspace` - Workspace files for web app

## Ports

- Frontend: `80` (HTTP)
- Backend: `8000` (API)

## Health Checks

Both services include health checks:
- Backend: `http://localhost:8000/docs`
- Frontend: `http://localhost/`

## GitHub Actions Auto-Deploy

The workflow automatically:
1. Builds Docker images on push to `main`
2. Pushes to GitHub Container Registry
3. (Optional) Deploys to your server via SSH

### Setup SSH Deploy

1. Add secrets to GitHub repository:
   - `SSH_HOST` - Your server IP/domain
   - `SSH_USER` - SSH username (e.g., `ubuntu`)
   - `SSH_PRIVATE_KEY` - Private SSH key

2. The deploy job will automatically pull and restart containers on push to `main`.

## Manual Deployment

```bash
# SSH into server
ssh user@your-server

# Navigate to project
cd /opt/window-aichat

# Pull latest
git pull origin main

# Rebuild and restart
docker-compose pull
docker-compose up -d --build
```

## Troubleshooting

### View logs
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Restart a service
```bash
docker-compose restart backend
docker-compose restart frontend
```

### Rebuild a service
```bash
docker-compose up -d --build backend
docker-compose up -d --build frontend
```

### Clean up
```bash
# Remove containers and volumes
docker-compose down -v

# Remove unused images
docker image prune -a
```
