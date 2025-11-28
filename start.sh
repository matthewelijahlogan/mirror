#!/bin/bash
set -e

echo "Installing dependencies..."
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

echo "Starting Mirror Mirror backend..."
exec uvicorn main:app --host 0.0.0.0 --port $PORT --log-level info
