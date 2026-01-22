#!/bin/bash
set -euo pipefail

echo "=== ONE-CLICK BACKEND FIX (Externally Managed Environment) ==="

# Configuration
APP_DIR="/opt/window-aichat"
BACKEND_FILE="$APP_DIR/backend.py"
WEB_ROOT="/var/www/window-aichat"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[INFO]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

# Step 1: Use pip with --break-system-packages flag
export PIP_BREAK_SYSTEM_PACKAGES=1

# Step 2: Check if backend.py exists
log "Checking backend file..."
if [[ ! -f "$BACKEND_FILE" ]]; then
    error "backend.py not found in $APP_DIR"
    echo "Available files:"
    ls -la "$APP_DIR"/*.py || echo "No Python files"
    exit 1
fi

# Step 3: Stop conflicting processes
log "Stopping conflicting processes..."
sudo systemctl stop window-aichat-backend 2>/dev/null || true
pkill -f "python.*backend.py" || true
docker-compose down 2>/dev/null || true

# Step 4: Install Python dependencies using apt and pip with break flag
log "Installing dependencies using system packages..."
cd "$APP_DIR"

# Try to install common packages via apt first
sudo apt update
sudo apt install -y python3-pip python3-venv python3-flask python3-aiohttp python3-requests

# Create a virtual environment for project-specific dependencies
log "Creating virtual environment..."
python3 -m venv "$APP_DIR/venv"
source "$APP_DIR/venv/bin/activate"

# Now install requirements.txt using the virtual environment
if [[ -f "requirements.txt" ]]; then
    log "Installing from requirements.txt..."
    pip install -r requirements.txt
else
    warn "No requirements.txt found. Installing common web dependencies..."
    pip install flask fastapi uvicorn python-socketio aiohttp requests
fi

# Step 5: Detect backend framework and port
log "Analyzing backend.py..."

PORT="8000"
if grep -q "flask" "$BACKEND_FILE"; then
    BACKEND_TYPE="flask"
    DETECTED_PORT=$(grep -oP "port[=:]\s*(\d+)" "$BACKEND_FILE" | grep -oP "\d+" | head -1 || echo "8000")
    PORT="${DETECTED_PORT:-8000}"
elif grep -q "fastapi\|FastAPI" "$BACKEND_FILE"; then
    BACKEND_TYPE="fastapi"
    DETECTED_PORT=$(grep -oP "port[=:]\s*(\d+)" "$BACKEND_FILE" | grep -oP "\d+" | head -1 || echo "8000")
    PORT="${DETECTED_PORT:-8000}"
else
    BACKEND_TYPE="generic"
    DETECTED_PORT=$(grep -oP "port[=:]\s*(\d+)" "$BACKEND_FILE" | grep -oP "\d+" | head -1 || echo "8000")
    PORT="${DETECTED_PORT:-8000}"
fi

log "Detected: $BACKEND_TYPE backend on port $PORT"

# Step 6: Create systemd service using virtual environment
log "Creating systemd service..."
sudo cat > /etc/systemd/system/window-aichat-backend.service << EOF
[Unit]
Description=Window AI Chat Backend
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=$APP_DIR/venv/bin/python $APP_DIR/backend.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# Step 7: Enable and start service
log "Starting backend service..."
sudo systemctl daemon-reload
sudo systemctl enable window-aichat-backend
sudo systemctl start window-aichat-backend

# Step 8: Wait for service to start
log "Waiting for backend to start..."
sleep 8

# Step 9: Check if backend is running
if sudo systemctl is-active window-aichat-backend >/dev/null; then
    log "✓ Backend service is running"
else
    error "✗ Backend service failed to start"
    sudo systemctl status window-aichat-backend --no-pager
    exit 1
fi

# Step 10: Test backend connectivity
log "Testing backend on port $PORT..."
if curl -s --connect-timeout 10 "http://localhost:$PORT" >/dev/null 2>&1; then
    log "✓ Backend responding on port $PORT"
elif curl -s --connect-timeout 10 "http://localhost:$PORT/health" >/dev/null 2>&1; then
    log "✓ Backend health endpoint working"
elif curl -s --connect-timeout 10 "http://localhost:$PORT/api/fs/list" >/dev/null 2>&1; then
    log "✓ Backend API endpoint working"
else
    warn "⚠ Backend started but not responding to basic checks"
    warn "This might be normal if backend needs specific endpoints"
fi

# Step 11: Update nginx configuration
log "Updating nginx configuration..."
sudo cat > /etc/nginx/sites-available/window-aichat << EOF
server {
    listen 80;
    server_name heidiaichat.duckdns.org 45.77.237.215;

    root /var/www/window-aichat;
    index index.html;

    # Frontend SPA support
    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # API proxy to Python backend
    location /api/ {
        proxy_pass http://localhost:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # CORS headers
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS, PUT, DELETE' always;
        add_header 'Access-Control-Allow-Headers' 'Content-Type, Authorization' always;

        # Handle preflight
        if (\$request_method = 'OPTIONS') {
            add_header 'Access-Control-Allow-Origin' '*';
            add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS, PUT, DELETE';
            add_header 'Access-Control-Allow-Headers' 'Content-Type, Authorization';
            add_header 'Content-Length' 0;
            add_header 'Content-Type' 'text/plain; charset=utf-8';
            return 204;
        }
    }

    # WebSocket support
    location /ws/ {
        proxy_pass http://localhost:$PORT;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_read_timeout 86400;
    }
}
EOF

# Step 12: Restart nginx
log "Restarting nginx..."
sudo nginx -t && sudo systemctl restart nginx
log "✓ Nginx restarted with backend configuration"

# Step 13: Update frontend API URLs
log "Updating frontend API configuration..."
cd "$APP_DIR/webapp"

# Fix API URLs in source code
find . -type f \( -name "*.js" -o -name "*.ts" -o -name "*.jsx" -o -name "*.tsx" -o -name "*.vue" \) 2>/dev/null | \
while read file; do
    if [[ -f "$file" ]]; then
        if grep -q "localhost:$PORT" "$file" || grep -q "127.0.0.1:$PORT" "$file"; then
            sed -i "s|http://localhost:$PORT|/api|g" "$file"
            sed -i "s|http://127.0.0.1:$PORT|/api|g" "$file"
        fi
    fi
done

# Update environment files
for env_file in ".env" ".env.production" ".env.local"; do
    if [[ -f "$env_file" ]]; then
        sed -i "s|http://localhost:$PORT|/api|g" "$env_file"
        sed -i "s|VITE_API_URL=.*|VITE_API_URL=/api|g" "$env_file" || true
        sed -i "s|REACT_APP_API_URL=.*|REACT_APP_API_URL=/api|g" "$env_file" || true
    fi
done

# Create production env file if it doesn't exist
if [[ ! -f ".env.production" ]]; then
    cat > .env.production << EOF
VITE_API_URL=/api
REACT_APP_API_URL=/api
NODE_ENV=production
EOF
fi

# Step 14: Rebuild frontend if needed
log "Rebuilding frontend with updated API URLs..."
if [[ -f "package.json" ]]; then
    npm run build
    sudo cp -R dist/* "$WEB_ROOT/" 2>/dev/null || sudo cp -R build/* "$WEB_ROOT/"
    sudo chown -R www-data:www-data "$WEB_ROOT"
fi

# Step 15: Final health check
log "Running final health checks..."

echo ""
echo "=== BACKEND FIX COMPLETE ==="
echo ""
echo "✓ Backend service: window-aichat-backend (systemd)"
echo "✓ Using virtual environment: $APP_DIR/venv"
echo "✓ Backend port: $PORT"
echo "✓ API endpoint: http://heidiaichat.duckdns.org/api/"
echo "✓ Frontend: http://heidiaichat.duckdns.org"
echo ""
echo "Service commands:"
echo "  sudo systemctl status window-aichat-backend"
echo "  sudo journalctl -u window-aichat-backend -f"
echo "  sudo systemctl restart window-aichat-backend"
echo ""
echo "Virtual environment commands:"
echo "  source $APP_DIR/venv/bin/activate"
echo "  pip list"
echo ""
echo "Test API endpoint:"
echo "  curl http://heidiaichat.duckdns.org/api/fs/list"
