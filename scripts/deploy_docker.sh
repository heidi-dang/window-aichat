#!/bin/bash

# ==============================================================================
# Docker-based Deployment Script for window-aichat
# Target: Ubuntu 24.04+ / 25.x VPS
# Deploys: FastAPI Backend + React Frontend using Docker Compose
# ==============================================================================

set -e # Exit on error

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_ROOT="/opt/window-aichat"
REPO_URL="https://github.com/heidi-dang/window-aichat.git"

echo -e "${BLUE}=== Docker Deployment for window-aichat ===${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
  echo -e "${RED}Please run as root (use sudo)${NC}"
  exit 1
fi

# --- 1. System Updates & Dependencies ---
echo -e "${GREEN}[1/6] Installing System Dependencies...${NC}"
apt-get update -y
apt-get install -y \
  git \
  curl \
  ufw \
  docker.io \
  docker-compose-plugin

# Start and enable Docker
systemctl start docker
systemctl enable docker

# Add current user to docker group (if not root)
if [ -n "$SUDO_USER" ]; then
  usermod -aG docker "$SUDO_USER"
fi

# --- 2. Clone/Update Repository ---
echo -e "${GREEN}[2/6] Setting up Repository...${NC}"
if [ -d "$PROJECT_ROOT/.git" ]; then
  echo "Repository exists, pulling latest changes..."
  cd "$PROJECT_ROOT"
  git pull origin main || git pull origin master
else
  echo "Cloning repository..."
  mkdir -p "$(dirname $PROJECT_ROOT)"
  git clone "$REPO_URL" "$PROJECT_ROOT"
  cd "$PROJECT_ROOT"
fi

# --- 3. Create Required Directories ---
echo -e "${GREEN}[3/6] Creating Required Directories...${NC}"
mkdir -p "$PROJECT_ROOT/server_cache/repo_cache"
mkdir -p "$PROJECT_ROOT/workspace"
chmod -R 755 "$PROJECT_ROOT/server_cache"
chmod -R 755 "$PROJECT_ROOT/workspace"

# --- 4. Build and Start Docker Containers ---
echo -e "${GREEN}[4/6] Building Docker Images...${NC}"
cd "$PROJECT_ROOT"

# Pull latest images if using production compose
if [ -f "docker-compose.prod.yml" ]; then
  echo "Using production images from GitHub Container Registry..."
  docker-compose -f docker-compose.prod.yml pull || echo "Images not found in registry, will build locally"
  docker-compose -f docker-compose.prod.yml up -d --build
else
  echo "Building images locally..."
  docker-compose up -d --build
fi

# --- 5. Firewall Setup ---
echo -e "${GREEN}[5/6] Configuring Firewall...${NC}"

# Allow SSH (Critical!)
ufw allow 22/tcp
ufw allow ssh

# Allow HTTP and HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# Allow backend port (if exposed externally)
ufw allow 8000/tcp || true

# Enable Firewall (Non-interactive)
echo "y" | ufw enable

# --- 6. Health Check ---
echo -e "${GREEN}[6/6] Checking Service Health...${NC}"

sleep 5

# Check backend
if curl -f http://localhost:8000/docs > /dev/null 2>&1; then
  echo -e "${GREEN}✓ Backend is running${NC}"
else
  echo -e "${YELLOW}⚠ Backend health check failed (may still be starting)${NC}"
fi

# Check frontend
if curl -f http://localhost/ > /dev/null 2>&1; then
  echo -e "${GREEN}✓ Frontend is running${NC}"
else
  echo -e "${YELLOW}⚠ Frontend health check failed (may still be starting)${NC}"
fi

# Show container status
echo -e "\n${BLUE}Container Status:${NC}"
docker-compose ps

# --- Summary ---
echo -e "\n${BLUE}====================================================${NC}"
echo -e "${GREEN}Docker Deployment Complete!${NC}"
echo -e "${BLUE}====================================================${NC}"
echo -e "Frontend: http://$(curl -s ifconfig.me || echo 'localhost')"
echo -e "Backend API: http://$(curl -s ifconfig.me || echo 'localhost'):8000"
echo -e "API Docs: http://$(curl -s ifconfig.me || echo 'localhost'):8000/docs"
echo -e "\n${YELLOW}Useful Commands:${NC}"
echo -e "  View logs:     docker-compose logs -f"
echo -e "  Stop services: docker-compose down"
echo -e "  Restart:       docker-compose restart"
echo -e "  Update:        cd $PROJECT_ROOT && git pull && docker-compose up -d --build"
echo -e "${BLUE}====================================================${NC}"
