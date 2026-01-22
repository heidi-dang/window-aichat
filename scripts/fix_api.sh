#!/bin/bash
set -euo pipefail

echo "=== Automatic API Call Fix Script ==="
echo "Fixing API endpoints and nginx configuration..."

# Configuration
DOMAIN="heidiaichat.duckdns.org"
BACKEND_PORT="8000"
WEB_ROOT="/var/www/window-aichat"
APP_DIR="/opt/window-aichat"
FRONTEND_DIR="/opt/window-aichat/webapp"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Function to log messages
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Step 1: Unmask and start nginx
log_info "Starting nginx..."
sudo systemctl unmask nginx >/dev/null 2>&1 || true
sudo systemctl enable nginx >/dev/null 2>&1 || true
sudo systemctl start nginx >/dev/null 2>&1 || true

# Step 2: Stop conflicting Docker containers
log_info "Stopping Docker containers to free port 80..."
docker-compose down >/dev/null 2>&1 || true
docker stop $(docker ps -q) >/dev/null 2>&1 || true

# Step 3: Fix nginx configuration
log_info "Creating optimized nginx configuration..."
sudo cat > /etc/nginx/sites-available/window-aichat << 'EOF'
server {
    listen 80;
    server_name heidiaichat.duckdns.org;

    # Frontend files
    location / {
        root /var/www/window-aichat;
        try_files $uri $uri/ /index.html;
        index index.html;
        
        # Security headers
        add_header X-Frame-Options SAMEORIGIN;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Referrer-Policy "strict-origin-when-cross-origin";
    }

    # API proxy to backend
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CORS headers
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS, PUT, DELETE' always;
        add_header 'Access-Control-Allow-Headers' 'Content-Type, Authorization' always;
        
        # Handle preflight requests
        if ($request_method = 'OPTIONS') {
            add_header 'Access-Control-Allow-Origin' '*';
            add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS, PUT, DELETE';
            add_header 'Access-Control-Allow-Headers' 'Content-Type, Authorization';
            add_header 'Content-Length' 0;
            add_header 'Content-Type' 'text/plain; charset=utf-8';
            return 204;
        }
    }

    # WebSocket proxy (if needed)
    location /ws/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }

    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
EOF

# Step 4: Enable the site
sudo ln -sf /etc/nginx/sites-available/window-aichat /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Step 5: Test and restart nginx
log_info "Testing nginx configuration..."
if sudo nginx -t; then
    sudo systemctl restart nginx
    log_info "Nginx configuration applied successfully"
else
    log_error "Nginx configuration test failed"
    exit 1
fi

# Step 6: Fix API endpoints in frontend code
log_info "Searching for API endpoint configurations..."
cd "$APP_DIR"

# Find and fix API URLs in frontend code
find "$FRONTEND_DIR" -type f \( -name "*.js" -o -name "*.ts" -o -name "*.jsx" -o -name "*.tsx" -o -name "*.vue" \) -exec grep -l "localhost:8000\|127.0.0.1:8000" {} \; | while read file; do
    log_info "Fixing API URL in: $file"
    sudo sed -i 's|http://localhost:8000|/api|g' "$file"
    sudo sed -i 's|http://127.0.0.1:8000|/api|g' "$file"
done

# Fix environment files
if [[ -f "$FRONTEND_DIR/.env" ]]; then
    log_info "Updating .env file..."
    sudo sed -i 's|http://localhost:8000|/api|g' "$FRONTEND_DIR/.env"
    sudo sed -i 's|VITE_API_URL=.*|VITE_API_URL=/api|g' "$FRONTEND_DIR/.env" || true
    sudo sed -i 's|REACT_APP_API_URL=.*|REACT_APP_API_URL=/api|g' "$FRONTEND_DIR/.env" || true
fi

# Create production environment file if it doesn't exist
if [[ ! -f "$FRONTEND_DIR/.env.production" ]]; then
    log_info "Creating .env.production file..."
    sudo cat > "$FRONTEND_DIR/.env.production" << 'EOF'
VITE_API_URL=/api
REACT_APP_API_URL=/api
GENERIC_API_URL=/api
NODE_ENV=production
EOF
fi

# Step 7: Ensure backend is running (if backend code exists)
if [[ -d "$APP_DIR/backend" ]]; then
    log_info "Checking backend service..."
    
    # Check if backend is running on port 8000
    if ! sudo netstat -tlnp | grep :8000 >/dev/null; then
        log_warn "Backend not running on port 8000. Attempting to start..."
        
        cd "$APP_DIR/backend"
        
        # Try different startup methods
        if [[ -f "package.json" ]]; then
            log_info "Starting Node.js backend..."
            npm install
            npm start &
        elif [[ -f "requirements.txt" ]]; then
            log_info "Starting Python backend..."
            pip install -r requirements.txt
            python app.py &
        elif [[ -f "docker-compose.yml" ]]; then
            log_info "Starting Docker backend..."
            docker-compose up -d
        else
            log_warn "No recognized backend configuration found"
        fi
        
        # Wait a moment for backend to start
        sleep 5
    else
        log_info "Backend seems to be running on port 8000"
    fi
else
    log_warn "No backend directory found at $APP_DIR/backend"
fi

# Step 8: Rebuild and deploy frontend
log_info "Rebuilding frontend..."
cd "$FRONTEND_DIR"

# Install dependencies if needed
if [[ -f "package.json" ]]; then
    log_info "Installing npm dependencies..."
    npm install
fi

# Build frontend
log_info "Building frontend..."
if npm run build; then
    # Deploy to web root
    log_info "Deploying to web root..."
    sudo mkdir -p "$WEB_ROOT"
    sudo rm -rf "$WEB_ROOT"/*
    
    # Find build directory
    if [[ -d "dist" ]]; then
        sudo cp -R dist/* "$WEB_ROOT"/
    elif [[ -d "build" ]]; then
        sudo cp -R build/* "$WEB_ROOT"/
    else
        log_error "No build directory found (dist/ or build/)"
        exit 1
    fi
    
    # Fix permissions
    sudo chown -R www-data:www-data "$WEB_ROOT"
    sudo chmod -R 755 "$WEB_ROOT"
else
    log_error "Frontend build failed"
    exit 1
fi

# Step 9: Final checks
log_info "Running final checks..."

# Check nginx is running
if sudo systemctl is-active nginx >/dev/null; then
    log_info "✓ Nginx is running"
else
    log_error "✗ Nginx is not running"
fi

# Check web files exist
if [[ -f "$WEB_ROOT/index.html" ]]; then
    log_info "✓ Frontend files deployed successfully"
else
    log_error "✗ index.html not found in web root"
fi

# Test API endpoint (if backend is supposed to be running)
if sudo netstat -tlnp | grep :8000 >/dev/null; then
    if curl -s http://localhost:8000/health >/dev/null 2>&1 || curl -s http://localhost:8000/api/fs/list >/dev/null 2>&1; then
        log_info "✓ Backend API is accessible"
    else
        log_warn "⚠ Backend is running but API endpoint may not be responding"
    fi
fi

# Test frontend locally
if curl -s http://localhost >/dev/null; then
    log_info "✓ Frontend is serving correctly"
else
    log_error "✗ Frontend not accessible on localhost"
fi

echo ""
echo "=== Fix Complete ==="
echo "Your application should now be accessible at:"
echo "HTTP:  http://$DOMAIN"
echo "API:   http://$DOMAIN/api/"
echo ""
echo "If you still encounter CORS issues:"
echo "1. Check that your backend includes CORS headers"
echo "2. Ensure all frontend API calls use relative paths (/api/ instead of http://localhost:8000)"
echo "3. Check browser console for specific error messages"

# Open in browser if possible
if command -v xdg-open >/dev/null; then
    xdg-open "http://$DOMAIN" >/dev/null 2>&1 &
elif command -v open >/dev/null; then
    open "http://$DOMAIN" >/dev/null 2>&1 &
fi
