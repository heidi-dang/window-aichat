# VPS Automated Deploy (Backend + Frontend)

This repo can deploy automatically to your VPS on every push to `main` using GitHub Actions.

## One-time VPS setup

1. Install Docker (and Docker Compose plugin).
2. Create the deploy directory:
   - `/opt/window-aichat`
3. Make sure these folders exist (they are mounted for persistence):
   - `/opt/window-aichat/server_cache`
   - `/opt/window-aichat/workspace`
4. Allow your SSH user to run Docker:
   - Either use `root`, or add the user to the `docker` group.
5. Ensure outbound HTTPS from the VPS to `ghcr.io` is allowed (image pulls).

## Required GitHub Secrets

Set these in your repo settings → Secrets and variables → Actions:

- `SSH_HOST` (VPS IP or hostname)
- `SSH_USER` (SSH username)
- `SSH_PRIVATE_KEY` (private key that matches a public key in `~/.ssh/authorized_keys` on VPS)
- `SSH_PORT` (optional, default `22`)
- `GHCR_USER` (GitHub username that can read GHCR images)
- `GHCR_PAT` (PAT with `read:packages` and (if private repo) `repo`)

## How deploy works (Docker Compose)

On push to `main`:

1. CI builds and pushes backend + frontend images to GHCR with tag:
   - `sha-<full_git_sha>`
2. Deploy job SSHes into the VPS and runs:
   - `docker login ghcr.io`
   - `docker compose -f docker-compose.prod.yml pull`
   - `docker compose -f docker-compose.prod.yml up -d --remove-orphans`
   - health checks (`/docs` and `/api/models`)

## Manual rollback

Pick a previous commit SHA and redeploy it by setting `IMAGE_TAG` on the VPS:

1. `cd /opt/window-aichat`
2. `export GHCR_REPO='heidi-dang/window-aichat'`
3. `export IMAGE_TAG='sha-<commit_sha>'`
4. `docker compose -f docker-compose.prod.yml pull`
5. `docker compose -f docker-compose.prod.yml up -d --remove-orphans`
