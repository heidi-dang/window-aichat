#!/bin/bash
# fix_deployment.sh

echo "=== Fixing Deployment Issues ==="

# 1. Install missing networking tools (fixes 'netstat not found')
echo "[1] Installing net-tools..."
sudo apt-get update -y
sudo apt-get install -y net-tools

# 2. Re-run build to ensure assets exist
echo "[2] Verifying Frontend Build..."
if [ ! -d "window-aichat-web/dist" ]; then
    echo "Build directory missing. Running build script..."
    bash build_web_app.sh
fi

# 3. Manually create directory and copy files (Fixes 'Directory MISSING')
echo "[3] Deploying Web Files..."
sudo mkdir -p /var/www/window-aichat
sudo cp -r window-aichat-web/dist/* /var/www/window-aichat/

# 4. Set Permissions
echo "[4] Setting Permissions..."
sudo chown -R www-data:www-data /var/www/window-aichat
sudo chmod -R 755 /var/www/window-aichat

# 5. Restart Nginx
echo "[5] Restarting Nginx..."
sudo systemctl restart nginx

# 6. Verify
echo "[6] Verification:"
if [ -d "/var/www/window-aichat" ]; then
    echo "✅ Web directory created successfully."
    ls -F /var/www/window-aichat | head -n 5
else
    echo "❌ Web directory still missing!"
fi

echo "=== Done. Try accessing your IP:8080 now. ==="