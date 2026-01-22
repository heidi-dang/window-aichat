#!/usr/bin/env bash
set -euo pipefail

############################################
# CONFIG – EDIT THESE VALUES BEFORE RUNNING
############################################

# GitHub repo
REPO_URL="https://github.com/heidi-dang/window-aichat.git"

# Where to install the app
APP_DIR="/opt/window-aichat"

# DuckDNS configuration
# Example: DOMAIN="mycoolapp" gives FQDN "mycoolapp.duckdns.org"
DOMAIN="YOUR_DUCKDNS_SUBDOMAIN_HERE"
DUCKDNS_TOKEN="YOUR_DUCKDNS_TOKEN_HERE"

# Optional: create / reuse a deploy SSH key for GitHub Actions auto-deploy
# This key will be created on the server and you will paste the public part into GitHub.
DEPLOY_KEY_NAME="window-aichat_deploy"

############################################
# BASIC CHECKS
############################################

if [[ "$EUID" -ne 0 ]]; then
  echo "Please run this script as root (e.g. sudo $0)"
  exit 1
fi

if [[ "$DOMAIN" == "YOUR_DUCKDNS_SUBDOMAIN_HERE" ]] || [[ "$DUCKDNS_TOKEN" == "YOUR_DUCKDNS_TOKEN_HERE" ]]; then
  echo "You must set DOMAIN and DUCKDNS_TOKEN at the top of this script before running."
  exit 1
fi

FQDN="${DOMAIN}.duckdns.org"
echo "Using domain: ${FQDN}"
sleep 2

############################################
# 1) SYSTEM PACKAGES (GIT, CURL, UFW)
############################################

apt-get update -y
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  git curl ufw ca-certificates gnupg lsb-release

############################################
# 2) INSTALL DOCKER (OFFICIAL REPOSITORY)
############################################

echo "Installing Docker from official repository..."

# Remove old versions if any
apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

# Add Docker's official GPG key
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

# Set up the repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine, CLI, and Docker Compose plugin
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Enable & start Docker
systemctl enable docker
systemctl start docker

# Verify Docker installation
if docker --version && docker compose version; then
  echo "✅ Docker and Docker Compose installed successfully"
else
  echo "❌ Docker installation failed"
  exit 1
fi

# Add current user to docker group (if not root)
if [ -n "$SUDO_USER" ]; then
  usermod -aG docker "$SUDO_USER"
  echo "Added $SUDO_USER to docker group (logout/login may be required)"
fi

############################################
# 3) CLONE OR UPDATE REPO
############################################

if [[ -d "${APP_DIR}/.git" ]]; then
  echo "Repo already exists at ${APP_DIR}, pulling latest changes..."
  git -C "${APP_DIR}" pull --rebase || git -C "${APP_DIR}" pull
else
  echo "Cloning repo into ${APP_DIR}..."
  mkdir -p "$(dirname "${APP_DIR}")"
  git clone "${REPO_URL}" "${APP_DIR}"
fi

cd "${APP_DIR}"

############################################
# 4) CREATE REQUIRED DIRECTORIES
############################################

mkdir -p "${APP_DIR}/server_cache/repo_cache"
mkdir -p "${APP_DIR}/workspace"
chmod -R 755 "${APP_DIR}/server_cache" "${APP_DIR}/workspace"

############################################
# 5) DUCKDNS SETUP (CRON-BASED)
############################################

echo "Setting up DuckDNS updater..."
DUCKDNS_DIR="/opt/duckdns"
mkdir -p "${DUCKDNS_DIR}"
DUCKDNS_SCRIPT="${DUCKDNS_DIR}/duckdns.sh"

cat > "${DUCKDNS_SCRIPT}" <<EOF
#!/usr/bin/env bash
set -e
echo "Updating DuckDNS at \$(date)"
curl -s "https://www.duckdns.org/update?domains=${DOMAIN}&token=${DUCKDNS_TOKEN}&ip=" >/var/log/duckdns.log 2>&1
EOF

chmod +x "${DUCKDNS_SCRIPT}"

CRON_FILE="/etc/cron.d/duckdns"
cat > "${CRON_FILE}" <<EOF
*/5 * * * * root ${DUCKDNS_SCRIPT}
EOF

systemctl restart cron 2>/dev/null || systemctl restart crond 2>/dev/null || true

echo "Waiting 10 seconds to give DuckDNS time to update DNS..."
sleep 10

############################################
# 6) FIREWALL (UFW)
############################################

echo "Configuring UFW firewall..."
ufw allow OpenSSH || true
ufw allow 22/tcp || true
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 8000/tcp || true   # backend port (optional)
yes | ufw enable || true

############################################
# 7) DOCKER DEPLOY (BACKEND + FRONTEND)
############################################

echo "Building and starting Docker containers with docker compose..."

# If production compose exists, prefer it (pre-built images),
# otherwise fall back to local build via docker-compose.yml.
if [[ -f "docker-compose.prod.yml" ]]; then
  echo "Using docker-compose.prod.yml (pre-built images)..."
  docker compose -f docker-compose.prod.yml pull || true
  docker compose -f docker-compose.prod.yml up -d --build
elif [[ -f "docker-compose.yml" ]]; then
  echo "Using docker-compose.yml (local build)..."
  docker compose up -d --build
else
  echo "ERROR: No docker-compose.yml or docker-compose.prod.yml found in ${APP_DIR}"
  exit 1
fi

############################################
# 8) BASIC HEALTH CHECKS
############################################

echo "Waiting a few seconds for containers to start..."
sleep 5

echo "Checking backend (http://localhost:8000/docs)..."
if curl -fsS "http://localhost:8000/docs" >/dev/null 2>&1; then
  echo "✅ Backend appears to be running."
else
  echo "⚠ Backend health check failed (may still be starting)."
fi

echo "Checking frontend (http://localhost/)..."
if curl -fsS "http://localhost/" >/dev/null 2>&1; then
  echo "✅ Frontend appears to be running."
else
  echo "⚠ Frontend health check failed (may still be starting)."
fi

############################################
# 9) OPTIONAL: PREPARE SERVER FOR GITHUB ACTIONS AUTO-DEPLOY
############################################

echo
echo "Setting up optional SSH deploy key for GitHub Actions (auto-deploy)..."

# Determine which user should own the deploy key (typically the sudo user)
TARGET_USER="${SUDO_USER:-root}"
TARGET_HOME="$(getent passwd "${TARGET_USER}" | cut -d: -f6 || echo "/root")"
TARGET_SSH_DIR="${TARGET_HOME}/.ssh"
DEPLOY_KEY_PATH="${TARGET_SSH_DIR}/${DEPLOY_KEY_NAME}"
DEPLOY_PUB_PATH="${DEPLOY_KEY_PATH}.pub"

mkdir -p "${TARGET_SSH_DIR}"
chmod 700 "${TARGET_SSH_DIR}"

# Create key if it doesn't exist
if [[ ! -f "${DEPLOY_KEY_PATH}" ]]; then
  echo "Generating new SSH key for ${TARGET_USER} at ${DEPLOY_KEY_PATH}..."
  sudo -u "${TARGET_USER}" ssh-keygen -t ed25519 -C "github-deploy-window-aichat" -f "${DEPLOY_KEY_PATH}" -N "" >/dev/null 2>&1
else
  echo "Deploy key already exists at ${DEPLOY_KEY_PATH}, reusing it."
fi

# Ensure public key is in authorized_keys
AUTHORIZED_KEYS="${TARGET_SSH_DIR}/authorized_keys"
touch "${AUTHORIZED_KEYS}"
chmod 600 "${AUTHORIZED_KEYS}"

PUB_KEY_CONTENT="$(cat "${DEPLOY_PUB_PATH}")"
if ! grep -q "${PUB_KEY_CONTENT}" "${AUTHORIZED_KEYS}" 2>/dev/null; then
  echo "Adding deploy public key to authorized_keys..."
  echo "${PUB_KEY_CONTENT}" >> "${AUTHORIZED_KEYS}"
fi

chown -R "${TARGET_USER}:${TARGET_USER}" "${TARGET_SSH_DIR}"

############################################
# 10) SUMMARY & GITHUB ACTIONS INSTRUCTIONS
############################################

PUBLIC_IP="$(curl -s ifconfig.me || echo 'YOUR_SERVER_IP')"

cat <<EOF

====================================================
window-aichat Docker deployment complete!

DuckDNS:
  Domain: ${FQDN}
  DuckDNS cron: ${CRON_FILE}

App URLs (HTTP):
  Frontend:  http://${FQDN}  (or http://${PUBLIC_IP})
  Backend:   http://${PUBLIC_IP}:8000
  API Docs:  http://${PUBLIC_IP}:8000/docs

Docker:
  Project dir:   ${APP_DIR}
  To see status: docker compose ps
  To see logs:   cd ${APP_DIR} && docker compose logs -f
  To restart:    cd ${APP_DIR} && docker compose restart
  To rebuild:    cd ${APP_DIR} && docker compose up -d --build

Firewall:
  Ports open: 22 (SSH), 80 (HTTP), 443 (HTTPS), 8000 (backend)

====================================================
GitHub Actions Auto-Deploy Setup (ONE-TIME)
====================================================

1) In your GitHub repo (heidi-dang/window-aichat):
   - Go to: Settings -> Secrets and variables -> Actions

2) Create these repository secrets:

   - SSH_HOST
     Value: ${PUBLIC_IP}  (or your DuckDNS name: ${FQDN})

   - SSH_USER
     Value: ${TARGET_USER}

   - SSH_PRIVATE_KEY
     Value: contents of: ${DEPLOY_KEY_PATH}
       (Copy everything, including:
        -----BEGIN OPENSSH PRIVATE KEY----- ... -----END OPENSSH PRIVATE KEY-----)

3) The corresponding public key (for your reference) is:
   File: ${DEPLOY_PUB_PATH}
   Value:
   ${PUB_KEY_CONTENT}

4) After secrets are set:
   - Push to main branch.
   - GitHub Actions workflow (ci-cd.yml) will:
     * Build/push Docker images
     * SSH into this server
     * Run docker compose pull/up to deploy

You now have:
- 1-click local deploy with this script
- 1-click GitHub Actions auto-deploy on git push
====================================================
EOF
