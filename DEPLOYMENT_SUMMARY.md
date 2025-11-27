# Mirror Mirror – Mobile App & Backend Deployment Summary

## Current Status

✅ **Local Development**
- Backend running on `http://172.28.139.137:8001` (your PC over WiFi)
- APK built and ready to sideload: `mirrorapp/platforms/android/app/build/outputs/apk/debug/app-debug.apk`
- Mobile app configured to connect to port 8001

✅ **Render.com Hosting (Ready to Deploy)**
- `render.yaml` and `Procfile` configured for automatic deployment
- `main.py` updated to support Render's `$PORT` environment variable
- Full deployment guide available in `RENDER_DEPLOYMENT.md`

## Quick Start

### Option 1: Local Testing (WiFi)

1. Ensure backend is running:
   ```powershell
   C:\Projects\mirror\venv\Scripts\uvicorn.exe main:app --host 0.0.0.0 --port 8001
   ```

2. On your phone (same WiFi), open the app and tap **Test Backend**
   - Should show connected and display quiz questions

3. Complete the quiz flow to test the full app experience locally

### Option 2: Deploy to Render.com

1. Push your repo to GitHub:
   ```bash
   git add -A
   git commit -m "Ready for production deployment"
   git push origin main
   ```

2. Go to https://dashboard.render.com and create a new Web Service
   - Select your GitHub repo
   - Use `Procfile` start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Set environment: `MIRROR_ALLOW_ALL_ORIGINS=true`

3. Deploy (takes 2–5 minutes)

4. Update app config to use your Render URL:
   ```javascript
   // In mirrorapp/www/js/config.js
   const API_BASE_URL = "https://mirror-mirror-backend.onrender.com";
   ```

5. Rebuild and sideload the APK

## Files Created/Updated for Deployment

| File | Purpose |
|------|---------|
| `render.yaml` | Render.com configuration (optional but helpful) |
| `Procfile` | Start command for Render/similar platforms |
| `RENDER_DEPLOYMENT.md` | Complete deployment guide |
| `run_as_render.bat` | Simulate Render startup locally (Windows) |
| `run_as_render.sh` | Simulate Render startup locally (Linux/Mac) |
| `mirrorapp/www/js/config-template.js` | Environment selector template |
| `main.py` | Updated to read `$PORT` from Render |

## Environment Variables

The backend respects these environment variables:

| Variable | Default | Used By |
|----------|---------|---------|
| `MIRROR_HOST` | `0.0.0.0` | Bind address (0.0.0.0 = all interfaces) |
| `PORT` | `8000` | **Render sets this automatically** |
| `MIRROR_PORT` | `8000` | Fallback if `PORT` not set |
| `MIRROR_ALLOW_ALL_ORIGINS` | `false` | Allow any origin (mobile app testing) |
| `ALLOWED_ORIGINS` | (dev defaults) | Comma-separated list of allowed CORS origins |
| `MIRROR_SECRET_KEY` | (random) | Session cookie encryption key |

## Testing Checklist

- [ ] Backend starts without errors locally
- [ ] `/quizdata` endpoint returns quiz questions
- [ ] Mobile app connects via "Test Backend" button
- [ ] Quiz flow works: answer questions → see fortune
- [ ] Render deployment health check passes
- [ ] Mobile app connects to Render backend from any network

## Troubleshooting

**Backend won't start:**
- Check that port 8001 (or your PORT) is not in use: `netstat -ano | Select-String ":8001"`
- Verify `question.json` exists in project root

**Mobile app shows "failed to fetch":**
- Ensure phone is on the same WiFi as PC (local) or has internet (Render)
- Check Windows Firewall allows port 8001 inbound
- Verify `API_BASE_URL` in `config.js` is correct

**Render deployment fails:**
- Check build logs in Render dashboard for import errors
- Ensure `requirements.txt` has all needed packages
- Verify `question.json` is committed to Git

## Next Steps

1. **Local testing complete?** → Sideload APK to phone and test locally
2. **Local testing successful?** → Deploy to Render and update `config.js` to use Render URL
3. **Ready for store submission?** → See main project README for store requirements

For detailed Render deployment steps, see `RENDER_DEPLOYMENT.md`.
