#!/usr/bin/env bash
# Local Render simulation
# This script mimics how Render.com will start your backend

# Set environment variables as Render would
export PORT=8000
export MIRROR_ALLOW_ALL_ORIGINS=true
export MIRROR_SECRET_KEY=dev-secret-key

# Start uvicorn on the simulated Render port
echo "Starting backend as Render would..."
echo "Listen on 0.0.0.0:$PORT"
echo "CORS: MIRROR_ALLOW_ALL_ORIGINS=$MIRROR_ALLOW_ALL_ORIGINS"

uvicorn main:app --host 0.0.0.0 --port $PORT
