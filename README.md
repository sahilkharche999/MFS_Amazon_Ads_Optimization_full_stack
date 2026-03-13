

# Project — Run & Development Guide

This repository can be run via `make` (recommended), with Docker only, or locally using Python and npm. Follow the sections below.

## Prerequisites
- Docker (and Docker Compose plugin or `docker-compose`)
- GNU `make`
- For local runs:
  - Python 3.8+ and `pip`
  - Node.js and `npm`

Copy the example env:
```bash
cp .env.example .env
# Fill secrets / DB values in .env (do not commit .env)
```

## Quick start — using `make` (recommended)
All targets assume `Makefile` is in the repo root.

- Check environment and tools:
  ```bash
  make env-check
  ```
- Build images:
  ```bash
  make build-images
  ```
- Validate configuration and scripts:
  ```bash
  make validate
  ```
- Start services (detached):
  ```bash
  make up
  ```
- Stop services:
  ```bash
  make down
  ```
- Rebuild images and restart:
  ```bash
  make rebuild
  ```

The `Makefile` detects `docker compose` (plugin) vs `docker-compose` (legacy) and uses whichever is available.

## Docker-only (no `make`)
Build images:
```bash
docker build -t mfs-frontend-image:latest -f frontend/Dockerfile frontend
docker build -t mfs-backend-image:latest -f backend/Dockerfile backend
```
Start services:
```bash
# prefer: docker compose (plugin)
docker compose up -d
# fallback:
# docker-compose up -d
```
Stop services:
```bash
docker compose down
```

## Local development — Python (backend) and npm (frontend)

Notes: local runs do not automatically provide dependent services (e.g., DB). Start DB via `make up` or `docker compose up` if required.

Frontend:
```bash
cd frontend
npm install
# start dev server (project may use `start` or `dev` script)
npm start
# or
npm run dev
```

Backend (generic steps):
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# load env vars from ../.env (bash)
set -a; source ../.env; set +a

# run the app (common variants)
# If FastAPI/uvicorn:
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Fallback if package/module entrypoint exists:
python -m backend
```
If the repository contains a backend-specific start command or `README` in `backend/`, prefer that command.

## Code documentation:

Repository layout (top-level):
- `frontend/` — React app (npm)
- `backend/` — Python app (pip)
- `docker-compose.yml` — service composition for local containers
- `Makefile` — convenience targets (see below)
- `scripts/` — helper scripts:
  - `scripts/build_images.sh` — build `mfs-frontend-image:latest` and `mfs-backend-image:latest`
- `.env.example` — template for environment variables (do not commit `.env`)

Makefile targets (summary):
- `help` — list available targets
- `build-images` — build frontend & backend Docker images
- `up` / `down` — start/stop services via compose
- `rebuild` — rebuild images and recreate services

Docker image names:
- `mfs-frontend-image:latest`
- `mfs-backend-image:latest`

Environment:
- create a local `.env`. Do not commit `.env` to VCS.

## Troubleshooting
- If `make` is missing, install via system package manager (e.g., `sudo yum install -y make` on Amazon Linux).
- If Docker Compose reports unset env vars, ensure `.env` exists and contains required keys.
- For permission issues with scripts, ensure executable bit is set:
  ```bash
  chmod +x scripts/*.sh
  ```