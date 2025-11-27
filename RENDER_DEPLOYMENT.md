# Render.com Deployment Guide for Mirror Mirror Backend

## Overview
This guide walks you through deploying the Mirror Mirror backend to Render.com, a free hosting platform. Once deployed, your mobile app can connect to a public HTTPS endpoint instead of a local network IP.

## Prerequisites
- A GitHub account (to connect your repo to Render)
- Your Mirror Mirror repository pushed to GitHub
- Render.com account (free tier available at https://render.com)

## Step 1: Prepare Your Repository

1. Ensure these files are in your project root:
   - `requirements.txt` — Python dependencies
   - `Procfile` — Start command for Render
   - `render.yaml` — (Optional) Render-specific config
   - `main.py` — FastAPI app
   - `templates/`, `static/`, `question.json` — App assets

2. Verify `requirements.txt` has all needed packages:
   ```
   fastapi
   uvicorn[standard]
   jinja2
   httpx
   python-multipart
   pydantic
   itsdangerous
   ```

3. Push all changes to GitHub:
   ```bash
   git add .
   git commit -m "Prepare for Render deployment"
   git push origin main
   ```

## Step 2: Create a Render Web Service

1. Go to https://dashboard.render.com
2. Click **New +** → **Web Service**
3. Choose **Deploy an existing repository**
   - Connect your GitHub account if prompted
   - Select your `mirror` repository
4. Configure the service:
   - **Name:** `mirror-mirror-backend` (or your choice)
   - **Environment:** Python 3 (or latest)
   - **Region:** Choose closest to you (e.g., Oregon, Frankfurt)
   - **Branch:** `main`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan:** Free (limited concurrency)

## Step 3: Configure Environment Variables

In the Render dashboard (Web Service → Environment):

| Key | Value | Notes |
|-----|-------|-------|
| `MIRROR_ALLOW_ALL_ORIGINS` | `true` | Allow requests from any origin (mobile app) |
| `MIRROR_SECRET_KEY` | (auto-generate) | Session encryption; Render can create this |
| `MIRROR_HOST` | `0.0.0.0` | Listen on all interfaces |
| `MIRROR_PORT` | (auto from $PORT) | Render sets this via $PORT variable |

**Note:** If you want to restrict CORS to specific origins later, set:
```
ALLOWED_ORIGINS=https://myapp.com,https://anotherapp.com
```

## Step 4: Deploy

1. Click **Create Web Service**
2. Render will automatically:
   - Build your app (install dependencies)
   - Deploy on a public HTTPS URL (e.g., `https://mirror-mirror-backend.onrender.com`)
   - Restart if you push new commits to `main`

3. Monitor build logs in the Render dashboard. Deployment typically takes 2–5 minutes.

## Step 5: Test the Deployment

Once deployed, test your backend:

```bash
# From your PC or phone browser:
curl https://mirror-mirror-backend.onrender.com/quizdata

# You should see JSON with quiz questions
```

If you see a **503 Service Unavailable** error:
- Check the build logs for errors (e.g., missing imports, syntax errors)
- Verify `requirements.txt` contains all dependencies
- Check that `main.py` loads `question.json` correctly

## Step 6: Update Your Mobile App to Use Render

Once your Render URL is confirmed working:

1. Update `mirrorapp/www/js/config.js`:
   ```javascript
   const API_BASE_URL = "https://mirror-mirror-backend.onrender.com";
   ```

2. Rebuild the Android APK:
   ```bash
   cd mirrorapp
   cordova build android
   ```

3. Sideload the new APK to your phone.

4. Open the app and tap **Test Backend**. It should now connect to your Render backend over the internet.

## Troubleshooting

### Build fails: "ModuleNotFoundError: No module named 'X'"
- **Fix:** Add the missing package to `requirements.txt` and push a new commit. Render auto-rebuilds.

### 503 Service Unavailable
- **Check:** Render logs (dashboard → Logs tab) for startup errors
- **Common cause:** `question.json` not found in the build. Ensure it's in your repo root.

### CORS errors on mobile
- **Check:** Environment variable `MIRROR_ALLOW_ALL_ORIGINS=true` is set
- **Alternative:** If restricting CORS, set `ALLOWED_ORIGINS=https://myapp.onrender.com`

### App still says "failed to fetch"
- **Check:** Ensure phone is connected to internet (not just WiFi with no internet)
- **Check:** Verify the `API_BASE_URL` in `config.js` matches your Render URL exactly
- **Check:** Render health check (dashboard) shows "Live" (green)

## Optional: Custom Domain

To use a custom domain (e.g., `api.yourdomain.com`):

1. In Render dashboard → Web Service → Settings → Custom Domain
2. Add your domain and follow DNS instructions
3. Update `config.js`:
   ```javascript
   const API_BASE_URL = "https://api.yourdomain.com";
   ```

## Free Tier Limits (Render)

- **Compute:** Shared CPU, 0.5 GB RAM
- **Concurrent requests:** ~10–20 (suitable for small testing)
- **Databases:** Not included (you're using SQLite locally, which persists locally on Render)
- **Always-on:** No; service spins down after 15 minutes of inactivity (cold start adds 30–60 seconds to first request)

For production, upgrade to a **Paid plan** for better performance.

## Next Steps

After deployment:

1. Test the full quiz → fortune flow on your phone with the Render backend.
2. If everything works, you can now distribute the APK to testers on any network (not just your home WiFi).
3. To prepare for App Store / Play Store, see your project's README for further guidance.

## Additional Resources

- [Render.com Docs](https://render.com/docs)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Uvicorn on Render](https://render.com/docs/deploy-uvicorn)
