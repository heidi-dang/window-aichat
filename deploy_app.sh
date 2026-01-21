#!/bin/bash

# ==============================================================================
# AI Chat Full Stack Deployment Script
# Target: Ubuntu 24.04+ / 25.x VPS
# Deploys: FastAPI Backend (Port 8000) + React Frontend (Nginx Port 8080)
# ==============================================================================

set -e # Exit on error

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

PROJECT_ROOT=$(pwd)
BACKEND_PORT=8000
DEPLOY_PORT=8080
SERVICE_NAME="aichat-backend"
WEB_DIR="/var/www/window-aichat"

echo -e "${BLUE}=== Starting AI Chat Deployment ===${NC}"

# --- 1. System Updates & Dependencies ---
echo -e "${GREEN}[1/7] Installing System Dependencies...${NC}"
sudo apt-get update -y
sudo apt-get install -y python3-pip python3-venv nodejs npm nginx git ufw acl

# Install Node.js LTS if version is too old
if [ "$(node -v | cut -d. -f1 | tr -d v)" -lt 18 ]; then
    echo "Node.js version too old. Installing latest LTS..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

# --- 2. Backend Setup ---
echo -e "${GREEN}[2/7] Setting up Python Backend...${NC}"

# Create Virtual Env
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Install Python Deps
source venv/bin/activate
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo -e "${RED}Error: requirements.txt not found!${NC}"
    exit 1
fi

# Create Systemd Service for Backend
echo -e "${GREEN}[3/7] Configuring Backend Service ($SERVICE_NAME)...${NC}"

cat <<EOF | sudo tee /etc/systemd/system/$SERVICE_NAME.service
[Unit]
Description=AI Chat FastAPI Backend
After=network.target

[Service]
User=$USER
WorkingDirectory=$PROJECT_ROOT
ExecStart=$PROJECT_ROOT/venv/bin/uvicorn backend:app --host 0.0.0.0 --port $BACKEND_PORT
Restart=always
Environment="PATH=$PROJECT_ROOT/venv/bin"

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl restart $SERVICE_NAME

# --- 3. Frontend Build ---
echo -e "${GREEN}[4/7] Building React Frontend...${NC}"

# Check if build script exists, otherwise we assume code is in 'window-aichat-web' or needs generation
if [ -f "build_web_app.sh" ]; then
    # Run the generator/builder script
    # We modify it slightly to skip system installs since we did that
    bash build_web_app.sh
else
    echo -e "${RED}Error: build_web_app.sh not found. Cannot generate frontend.${NC}"
    exit 1
fi

# Verify Build
if [ -d "window-aichat-web/dist" ]; then
    echo "Build successful."
else
    echo -e "${RED}Frontend build failed. 'dist' directory missing.${NC}"
    exit 1
fi

# --- 4. Deploy Frontend to Nginx Location ---
echo -e "${GREEN}[5/7] Deploying to Web Directory...${NC}"
sudo mkdir -p $WEB_DIR
# Clear old files
sudo rm -rf $WEB_DIR/*
# Copy new build
sudo cp -r window-aichat-web/dist/* $WEB_DIR/
# Set permissions
sudo chown -R www-data:www-data $WEB_DIR
sudo chmod -R 755 $WEB_DIR

# --- 5. Nginx Configuration ---
echo -e "${GREEN}[6/7] Configuring Nginx Reverse Proxy...${NC}"

cat <<EOF | sudo tee /etc/nginx/sites-available/window-aichat
server {
    listen $DEPLOY_PORT;
    server_name _;

    root $WEB_DIR;
    index index.html;

    # Frontend Routes (SPA Support)
    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # Backend API Proxy
    location /api {
        proxy_pass http://127.0.0.1:$BACKEND_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }

    # WebSocket Proxy (Terminal)
    location /ws {
        proxy_pass http://127.0.0.1:$BACKEND_PORT;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}
EOF

# Enable Site
sudo ln -sf /etc/nginx/sites-available/window-aichat /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default  # Remove default if it conflicts

# Test and Restart Nginx
sudo nginx -t
sudo systemctl restart nginx

# --- 6. Firewall Setup ---
echo -e "${GREEN}[7/7] Configuring Firewall...${NC}"

# Allow SSH (Critical!)
sudo ufw allow 22/tcp
sudo ufw allow ssh

# Allow App Port
sudo ufw allow $DEPLOY_PORT/tcp

# Enable Firewall (Non-interactive)
echo "y" | sudo ufw enable

echo -e "${BLUE}====================================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "Access your app at: http://$(curl -s ifconfig.me):$DEPLOY_PORT"
echo -e "${BLUE}====================================================${NC}"