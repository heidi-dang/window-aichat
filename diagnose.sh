#!/bin/bash
# Save as diagnose.sh and run with: bash diagnose.sh

echo "==============================================="
echo "   AI CHAT DEPLOYMENT DIAGNOSTIC TOOL"
echo "==============================================="

# 1. Check if Nginx is running
echo -e "\n[1] Checking Nginx Service..."
if systemctl is-active --quiet nginx; then
    echo "✅ Nginx is RUNNING"
else
    echo "❌ Nginx is NOT RUNNING"
    sudo systemctl status nginx --no-pager
fi

# 2. Check if Backend is running
echo -e "\n[2] Checking Backend Service..."
if systemctl is-active --quiet aichat-backend; then
    echo "✅ Backend is RUNNING"
else
    echo "❌ Backend is NOT RUNNING"
    sudo systemctl status aichat-backend --no-pager
fi

# 3. Check Ports
echo -e "\n[3] Checking Ports (8080 & 8000)..."
PORTS=$(sudo netstat -tulpn | grep -E ':(8080|8000)')
if [[ $PORTS == *":8080"* ]]; then
    echo "✅ Port 8080 (Frontend) is LISTENING"
else
    echo "❌ Port 8080 is NOT LISTENING (Nginx issue)"
fi

# 4. Check Firewall
echo -e "\n[4] Checking UFW Firewall..."
sudo ufw status | grep 8080

# 5. Check Web Directory
echo -e "\n[5] Checking Web Directory..."
if [ -d "/var/www/window-aichat" ]; then
    FILE_COUNT=$(ls /var/www/window-aichat | wc -l)
    echo "✅ Web directory exists with $FILE_COUNT files"
else
    echo "❌ Web directory /var/www/window-aichat MISSING"
fi

echo -e "\n==============================================="