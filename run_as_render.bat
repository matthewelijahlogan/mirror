@echo off
REM Local Render simulation (Windows)
REM This script mimics how Render.com will start your backend

REM Set environment variables as Render would
set PORT=8000
set MIRROR_ALLOW_ALL_ORIGINS=true
set MIRROR_SECRET_KEY=dev-secret-key

REM Start uvicorn on the simulated Render port
echo Starting backend as Render would...
echo Listen on 0.0.0.0:%PORT%
echo CORS: MIRROR_ALLOW_ALL_ORIGINS=%MIRROR_ALLOW_ALL_ORIGINS%

call C:\Projects\mirror\venv\Scripts\uvicorn.exe main:app --host 0.0.0.0 --port %PORT%
