# Packaging: Cordova-ready www bundle

This folder contains a ready-to-use `www/` bundle you can copy into a Cordova project to build an APK.

Contents:
- `www/index.html` — Landing page
- `www/quiz.html` — Quiz UI (single-page style)
- `www/fortune.html` — Fortune display
- `www/css/style.css` — Styling (trimmed placeholder; copy full `static/css/style.css` if desired)
- `www/js/config.js` — Set `API_BASE_URL` here to point to your backend (e.g. `https://<ngrok>.io`)
- `www/js/quiz.js` — Modified quiz script that uses `API_BASE_URL`
- `www/data/question.json` — Local question fallback

How to use (high level):

1. Install Node.js & Cordova on your machine (https://nodejs.org/ and `npm install -g cordova`).
2. Create a Cordova project:

```powershell
cordova create mirrorapp com.example.mirror MirrorApp
cd mirrorapp
```

3. Replace `mirrorapp/www` with the contents of `packaging/cordova/www` (copy files over).

4. Edit `www/js/config.js` and set `API_BASE_URL` to your backend endpoint (must be HTTPS for store builds):

```js
const API_BASE_URL = 'https://your-backend.example.com';
```

5. Add Android platform and build:

```powershell
cordova platform add android
cordova build android --release
# or run on device
cordova run android --device
```

Notes:
- For local testing you can expose your dev server via `ngrok` and set `API_BASE_URL` to the generated HTTPS URL.
- If you prefer Capacitor, similar steps apply — copy the `www` folder into the Capacitor app and run `npx cap add android`.
- Before publishing to Play Store, sign the APK and follow Android publishing guides.

