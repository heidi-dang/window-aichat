# Docker & GitHub Actions Setup Complete ✅

## What Was Created

### 1. **Docker Files**
- `Dockerfile.backend` - Python/FastAPI backend container
- `Dockerfile.frontend` - React/Vite frontend with Nginx
- `docker-compose.yml` - Local development setup
- `docker-compose.prod.yml` - Production setup using pre-built images
- `.dockerignore` - Excludes unnecessary files from builds
- `nginx.conf` - Nginx config for frontend with API proxy

### 2. **GitHub Actions Workflows**
- `.github/workflows/ci-cd.yml` - Full CI/CD pipeline:
  - Lints and tests backend
  - Builds and tests frontend
  - Builds and pushes Docker images to GitHub Container Registry
  - Optional auto-deploy to server via SSH
- `.github/workflows/docker-build.yml` - Simplified Docker build workflow

### 3. **Deployment Scripts**
- `scripts/deploy_docker.sh` - One-command Docker deployment script

### 4. **Documentation**
- `DEPLOY.md` - Complete deployment guide
- `DOCKER_SETUP.md` - This file

## Quick Start

### Local Development

```bash
# Build and start
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Production Deployment

```bash
# On your Ubuntu server
sudo bash scripts/deploy_docker.sh
```

Or manually:

```bash
git clone https://github.com/heidi-dang/window-aichat.git
cd window-aichat
docker-compose up -d --build
```

## GitHub Actions Auto-Build

### What Happens on Git Push

1. **On Push to `main` branch:**
   - ✅ Backend: Lint → Test → Build Docker image → Push to `ghcr.io`
   - ✅ Frontend: Lint → Build → Build Docker image → Push to `ghcr.io`
   - ✅ (Optional) Auto-deploy to your server

2. **On Pull Request:**
   - ✅ Runs tests and builds (but doesn't push images)

### Image Locations

After pushing to `main`, your images will be at:
- `ghcr.io/heidi-dang/window-aichat/backend:latest`
- `ghcr.io/heidi-dang/window-aichat/frontend:latest`

### Setup Auto-Deploy (Optional)

1. Go to GitHub repo → Settings → Secrets and variables → Actions
2. Add these secrets:
   - `SSH_HOST` - Your server IP (e.g., `123.45.67.89`)
   - `SSH_USER` - SSH username (e.g., `ubuntu`)
   - `SSH_PRIVATE_KEY` - Your private SSH key content

3. The workflow will automatically deploy on push to `main`

## Manual Deployment from Registry

```bash
# Pull and run pre-built images
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

## Ports

- **Frontend**: Port `80` (HTTP)
- **Backend API**: Port `8000`
- **API Docs**: `http://your-server:8000/docs`

## Volumes (Persistent Data)

- `./server_cache` - Backend cache and GitHub repo cache
- `./workspace` - Workspace files for web app

## Troubleshooting

### View Logs
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Restart Services
```bash
docker-compose restart
```

### Rebuild After Code Changes
```bash
git pull
docker-compose up -d --build
```

### Clean Everything
```bash
docker-compose down -v
docker system prune -a
```

## Next Steps

1. **Test locally**: `docker-compose up -d --build`
2. **Push to GitHub**: Your workflow will auto-build images
3. **Deploy to server**: Use `scripts/deploy_docker.sh` or manual steps
4. **Set up auto-deploy**: Add SSH secrets to GitHub for automatic deployment

## Notes

- Frontend build uses `NODE_OPTIONS=--max-old-space-size=4096` to handle Monaco Editor's large size
- Backend health check: `http://localhost:8000/docs`
- Frontend health check: `http://localhost/`
- All services restart automatically on failure (`restart: unless-stopped`)
