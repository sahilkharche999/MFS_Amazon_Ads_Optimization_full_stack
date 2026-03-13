#!/usr/bin/env bash
set -euo pipefail

# Build frontend and backend docker images using the existing Dockerfiles
# Usage: ./scripts/build_images.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Project root: $ROOT_DIR"

# Frontend image
echo "Building frontend image: mfs-frontend-image:latest"
docker build -t mfs-frontend-image:latest -f "$ROOT_DIR/frontend/Dockerfile" "$ROOT_DIR/frontend"

# Backend image
echo "Building backend image: mfs-backend-image:latest"
docker build -t mfs-backend-image:latest -f "$ROOT_DIR/backend/Dockerfile" "$ROOT_DIR/backend"

echo "Build complete. Images: mfs-frontend-image:latest, mfs-backend-image:latest"
