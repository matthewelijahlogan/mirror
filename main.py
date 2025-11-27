"""
main.py — Expanded Mirror Mirror Backend (v3.0) — Robust edition
===============================================================
Notes:
- Preserves original behavior while adding:
  - /fortune page (renders latest or query-provided fortune)
  - /fortune_data JSON endpoint (for client-side fetch)
  - / (landing index) and /quiz endpoints (ensures templates + static resolve)
  - defensive checks for static/template/question files
  - clearer logging for debugging 404s on static assets
- Assumes quiz_logic.QuizEngine exists (see your quiz_logic.py) and fortune_engine functions present.
"""

import os
import json
import random
import traceback
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware

# Existing imports preserved
# fortune_engine must expose generate_fortune and get_user_history
from fortune_engine import generate_fortune, get_user_history
from astrology import analyze_zodiac, astrology_hint
from database import DatabaseHandler
from quiz_logic import QuizEngine, process_quiz

# ============================================================
# CONFIG
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
QUESTION_FILE = os.path.join(BASE_DIR, "question.json")  # used as fallback if /static/data/question.json exists
SECRET_KEY = os.environ.get("MIRROR_SECRET_KEY", "supersecretmirrorkey")
# Allow overriding host/port via environment for easier device testing and cloud deployment
# Render.com and similar platforms set $PORT automatically
HOST = os.environ.get("MIRROR_HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT") or os.environ.get("MIRROR_PORT") or "8000")

# FastAPI app + static + templates
app = FastAPI(title="Mirror Mirror Backend", debug=False)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# CORS configuration: control via `ALLOWED_ORIGINS` (comma-separated) or
# enable permissive mode with `MIRROR_ALLOW_ALL_ORIGINS=true` for quick testing.
ALLOW_ALL_ORIGINS = os.environ.get("MIRROR_ALLOW_ALL_ORIGINS", "false").lower() in ("1", "true", "yes")
allowed_env = os.environ.get("ALLOWED_ORIGINS")
if ALLOW_ALL_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    if allowed_env:
        origins = [o.strip() for o in allowed_env.split(",") if o.strip()]
    else:
        # sensible dev defaults; add your app origin(s) via ALLOWED_ORIGINS
        origins = ["http://localhost:8000", "http://127.0.0.1:8000"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    print(f"[main] CORS allowed origins: {origins}")

# Defensive: ensure static dir exists
if not os.path.isdir(STATIC_DIR):
    print(f"[main WARNING] static directory missing at expected path: {STATIC_DIR}")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Ensure templates dir exists
if not os.path.isdir(TEMPLATES_DIR):
    print(f"[main WARNING] templates directory missing at expected path: {TEMPLATES_DIR}")

# Initialize Database handler and QuizEngine
db = DatabaseHandler(os.path.join(BASE_DIR, "mirror.db"))
quiz_engine = QuizEngine(QUESTION_FILE)

# Expanded global analytics store
analytics_data = {
    "total_submissions": 0,
    "names_counter": {},
    "traits_counter": {},
    "zodiac_counter": {},
    "error_events": []
}

# ============================================================
# Logging helpers
# ============================================================
def log_debug(msg: str):
    print(f"[{datetime.now().isoformat()}] DEBUG: {msg}")

def log_error(msg: str):
    print(f"[{datetime.now().isoformat()}] ERROR: {msg}")
    analytics_data["error_events"].append({
        "timestamp": datetime.now().isoformat(),
        "message": str(msg)[:1000]
    })

def dump_debug_state() -> dict:
    """Return introspection data for /debug/system"""
    try:
        qb_size = getattr(quiz_engine, "question_count", None)
        return {
            "analytics": analytics_data,
            "question_bank_size": qb_size,
            "db_path": getattr(db, "db_path", str(os.path.join(BASE_DIR, "mirror.db"))),
            "config": {
                "static_dir": STATIC_DIR,
                "templates_dir": TEMPLATES_DIR,
                "question_file": QUESTION_FILE
            }
        }
    except Exception as e:
        log_error(f"dump_debug_state failed: {e}")
        return {"error": "dump failed"}

# ============================================================
# Session helpers
# ============================================================
def get_session_profile(request: Request) -> dict:
    return request.session.get("profile", {})

def set_session_profile(request: Request, profile: dict):
    request.session["profile"] = profile
    if "session_start" not in request.session:
        request.session["session_start"] = datetime.now().isoformat()
    request.session["last_activity"] = datetime.now().isoformat()
    request.session["submissions"] = request.session.get("submissions", 0) + 1

def clear_session_profile(request: Request):
    for k in ["profile", "session_start", "last_activity", "submissions"]:
        request.session.pop(k, None)

def get_session_metrics(request: Request) -> dict:
    return {
        "session_start": request.session.get("session_start"),
        "last_activity": request.session.get("last_activity"),
        "submissions": request.session.get("submissions", 0)
    }

# ============================================================
# General helpers
# ============================================================
def sanitize_name(name: str) -> str:
    return "".join(c for c in (name or "") if c.isalnum() or c in " _-").strip() or "Wanderer"

def format_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def update_analytics(name: str, profile: Optional[dict] = None):
    analytics_data["total_submissions"] += 1
    analytics_data["names_counter"].setdefault(name, 0)
    analytics_data["names_counter"][name] += 1
    if profile:
        for k, v in profile.items():
            analytics_data["traits_counter"].setdefault(k, {})
            analytics_data["traits_counter"][k].setdefault(str(v), 0)
            analytics_data["traits_counter"][k][str(v)] += 1

def compute_quiz_summary(profile: dict) -> dict:
    if not profile:
        return {}
    try:
        # Ensure values are strings to satisfy process_quiz expectations
        def _s(k):
            v = profile.get(k)
            return str(v) if v is not None else ""

        return process_quiz(
            mood=_s("mood"),
            focus=_s("focus"),
            trust=_s("trust"),
            creativity=_s("creativity"),
            patience=_s("patience"),
            empathy=_s("empathy")
        )
    except Exception:
        log_error(f"compute_quiz_summary failed: {traceback.format_exc()}")
        return {}

# ============================================================
# ML pipeline prep
# ============================================================
def ml_feature_vector(name, birthdate, profile):
    """Transforms user data into a structured ML-ready vector."""
    zodiac, element = analyze_zodiac(birthdate)
    analytics_data["zodiac_counter"].setdefault(zodiac, 0)
    analytics_data["zodiac_counter"][zodiac] += 1
    numeric_traits = {k: int(v) if str(v).isdigit() else 0 for k, v in (profile or {}).items()}
    return {
        "name_len": len(name or ""),
        "birth_year": int(birthdate.split("-")[0]) if birthdate and "-" in birthdate else 1900,
        "zodiac": zodiac,
        "element": element,
        "traits": numeric_traits
    }

def save_ml_training_record(payload):
    """Appends a training datapoint to ml_training.json for future ML model."""
    out_file = os.path.join(BASE_DIR, "ml_training.json")
    try:
        data = []
        if os.path.exists(out_file):
            with open(out_file, "r", encoding="utf-8") as fh:
                try:
                    data = json.load(fh)
                except Exception:
                    data = []
        data.append(payload)
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log_error(f"save_ml_training_record failed: {e}")

def save_quiz_result(payload: dict):
    """Append quiz result to `quiz_results.json` for easy bulk export and offline analysis."""
    out_file = os.path.join(BASE_DIR, "quiz_results.json")
    try:
        data = []
        if os.path.exists(out_file):
            with open(out_file, "r", encoding="utf-8") as fh:
                try:
                    data = json.load(fh)
                except Exception:
                    data = []
        data.append(payload)
        # atomic write
        tmp = out_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        os.replace(tmp, out_file)
    except Exception as e:
        log_error(f"save_quiz_result failed: {e}")

# ============================================================
# ROUTES — pages & data endpoints
# ============================================================

# Landing page — use index.html (keeps UI consistent)
@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception:
        log_error(f"landing() failure: {traceback.format_exc()}")
        # Fallback simple HTML
        return HTMLResponse("<h1>Mirror Mirror</h1><p>Landing page error.</p>", status_code=500)

# Quiz page — renders quiz.html and supplies initial questions
@app.get("/quiz", response_class=HTMLResponse)
async def quiz_page(request: Request):
    try:
        # load some sample questions from quiz_engine if available
        questions = []
        try:
            questions = quiz_engine.get_randomized_questions(6)
        except Exception:
            # Attempt to read a static fallback question file inside static/data
            fallback_path = os.path.join(STATIC_DIR, "data", "question.json")
            if os.path.exists(fallback_path):
                try:
                    with open(fallback_path, "r", encoding="utf-8") as fh:
                        questions = json.load(fh)
                except Exception:
                    questions = []
        return templates.TemplateResponse("quiz.html", {"request": request, "questions": questions, "timestamp": format_timestamp()})
    except Exception:
        log_error(f"quiz_page() failure: {traceback.format_exc()}")
        return HTMLResponse("<h1>Error loading quiz page</h1>", status_code=500)

# JSON endpoint for client to request questions (used by quiz.js)
@app.get("/quizdata")
def get_quizdata(request: Request):
    try:
        # Preferred: use quiz_logic helpers if they exist
        try:
            from quiz_logic import load_questions, randomize_questions
            all_questions = load_questions()
            selected = randomize_questions(all_questions, 6)
            return {"questions": selected}
        except Exception:
            # Fallback: try QuizEngine methods
            try:
                if hasattr(quiz_engine, "get_randomized_questions"):
                    selected = quiz_engine.get_randomized_questions(6)
                    return {"questions": selected}
            except Exception:
                pass

            # Fallback: static data file
            fallback_path = os.path.join(STATIC_DIR, "data", "question.json")
            if os.path.exists(fallback_path):
                try:
                    with open(fallback_path, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                        if isinstance(data, dict) and "questions" in data:
                            base_questions = data["questions"]
                        elif isinstance(data, list):
                            base_questions = data
                        else:
                            base_questions = []
                except Exception as e:
                    log_error(f"Failed reading fallback question file: {e}")
                    base_questions = []
                # If session contains profile data, append generated followups
                try:
                    profile = request.session.get('profile', {})
                    if profile and hasattr(quiz_engine, 'generate_followup_questions'):
                        followups = quiz_engine.generate_followup_questions(profile, n=3)
                        base_questions = (base_questions or []) + followups
                except Exception:
                    pass
                return {"questions": base_questions}

        # If we reach here no source found
        log_error("/quizdata: no question source available")
        return JSONResponse({"questions": []}, status_code=500)
    except Exception as exc:
        log_error(f"/quizdata unexpected error: {exc}")
        return JSONResponse({"questions": []}, status_code=500)

# Submit quiz form — receives JSON data (from quiz.js) or form-encoded (legacy)
@app.post("/submit", response_class=JSONResponse)
async def submit_quiz(request: Request):
    try:
        # Determine content type and parse accordingly
        content_type = request.headers.get("content-type", "")
        
        if "application/json" in content_type:
            # Handle JSON from quiz.js
            data = await request.json()
            name = sanitize_name(data.get("name", "Wanderer"))
            birthdate = data.get("birthdate", "1900-01-01")
            profile = data.get("quiz", {})
        else:
            # Handle form-encoded (legacy)
            form = await request.form()
            name = sanitize_name(form.get("name", "Wanderer"))
            birthdate = form.get("birthdate", "1900-01-01")
            
            # extract quiz answers
            profile = {}
            for key, val in form.items():
                # Accept q_ prefixed keys OR the canonical trait names
                if key.startswith("q_"):
                    profile[key[2:]] = val
                elif key in ["mood", "focus", "trust", "creativity", "patience", "empathy"]:
                    profile[key] = val
                else:
                    # also accept numeric sliders (range inputs)
                    try:
                        if str(val).isdigit():
                            profile[key] = int(val)
                        else:
                            profile[key] = val
                    except Exception:
                        profile[key] = val

        # session + analytics
        set_session_profile(request, profile)
        update_analytics(name, profile)

        # Build user data and generate fortune
        user_data = {"name": name, "birthdate": birthdate, "quiz": profile}
        fortune_text = generate_fortune(user_data)

        # Save to DB (defensive call - DatabaseHandler should implement save_user_result)
        try:
            db.save_user_result(name, birthdate, profile, fortune_text)
        except Exception as e:
            log_error(f"db.save_user_result failed: {e}")

        # persist ML record
        training_record = ml_feature_vector(name, birthdate, profile)
        save_ml_training_record(training_record)

        # persist to single JSON results file for bulk export/analysis
        try:
            save_quiz_result({
                "timestamp": format_timestamp(),
                "name": name,
                "birthdate": birthdate,
                "profile": profile,
                "fortune": fortune_text
            })
        except Exception as e:
            log_error(f"save_quiz_result call failed: {e}")

        # Compose hints and include astrology data
        hints = compute_quiz_summary(profile)
        zodiac, element = analyze_zodiac(birthdate)
        hints.update({"zodiac": zodiac, "element": element})

        # store small session-level last fortune for quick rendering
        request.session["last_fortune"] = fortune_text

        return JSONResponse({
            "fortune": fortune_text,
            "profile": profile,
            "hints": hints,
            "session_metrics": get_session_metrics(request),
            "timestamp": format_timestamp()
        })
    except Exception:
        log_error(f"submit_quiz() crash: {traceback.format_exc()}")
        return JSONResponse({"error": "Failed to process quiz."}, status_code=500)

# Fortune page — renders fortune.html and tries to find the best fortune to show
@app.get("/fortune", response_class=HTMLResponse)
async def fortune_page(request: Request, name: Optional[str] = None, fortune: Optional[str] = None):
    try:
        # Priority:
        # 1) explicit fortune query param
        # 2) session-stored last_fortune
        # 3) user history lookup by name (most recent)
        # 4) fallback message
        txt = ""
        if fortune:
            txt = fortune
        else:
            sess = request.session
            txt = sess.get("last_fortune", "")

        if (not txt) and name:
            try:
                history = get_user_history(sanitize_name(name))
                if history:
                    # fortune_engine.get_user_history returns list of entries (newest-first or oldest-first depending impl)
                    # use last element if stored oldest-first; try newest-first first
                    if isinstance(history, list) and history:
                        # pick newest if entry has timestamp
                        try:
                            # assume entries have 'timestamp' and 'fortune'
                            latest = sorted(history, key=lambda e: e.get("timestamp", ""), reverse=True)[0]
                            txt = latest.get("fortune", "")
                        except Exception:
                            # fallback to last entry
                            txt = history[-1].get("fortune", "") if history[-1].get("fortune") else ""
            except Exception:
                log_debug(f"fortune_page: get_user_history failed for {name}")

        if not txt:
            txt = "The mirror is quiet right now. Stand before it and speak your truth."

        return templates.TemplateResponse("fortune.html", {"request": request, "fortune": txt})
    except Exception:
        log_error(f"fortune_page() crash: {traceback.format_exc()}")
        return HTMLResponse("<h1>Error loading fortune</h1>", status_code=500)

# Fortune JSON endpoint — useful for client-only rendering or API consumers
@app.get("/fortune_data", response_class=JSONResponse)
async def fortune_data(name: Optional[str] = None):
    try:
        if name:
            hist = get_user_history(sanitize_name(name))
            if hist:
                # return newest entry if available
                latest = sorted(hist, key=lambda e: e.get("timestamp", ""), reverse=True)[0]
                return JSONResponse({"fortune": latest.get("fortune", "")})
        # default sample fortune (generator expects user_data; we pass minimal)
        sample = generate_fortune({"name": "Wanderer", "birthdate": "1900-01-01", "quiz": {}})
        return JSONResponse({"fortune": sample})
    except Exception:
        log_error(f"fortune_data() crash: {traceback.format_exc()}")
        return JSONResponse({"fortune": "The mirror is quiet."}, status_code=500)

# ============================================================
# User history / analytics / debug endpoints
# ============================================================

@app.get("/history/{username}", response_class=JSONResponse)
async def user_history(username: str):
    try:
        uns = sanitize_name(username)
        history = db.get_user_history(uns)
        return JSONResponse({"history": history})
    except Exception:
        log_error(f"user_history() crash: {traceback.format_exc()}")
        return JSONResponse({"history": []})

@app.get("/analytics", response_class=JSONResponse)
async def analytics():
    try:
        top_names = sorted(analytics_data["names_counter"].items(), key=lambda x: x[1], reverse=True)
        return JSONResponse({
            "total_submissions": analytics_data["total_submissions"],
            "top_names": top_names[:10],
            "zodiac_distribution": analytics_data["zodiac_counter"]
        })
    except Exception:
        log_error(f"analytics() crash: {traceback.format_exc()}")
        return JSONResponse({"error": "analytics failed"}, status_code=500)


@app.get("/admin/download_results", response_class=JSONResponse)
async def download_results(token: Optional[str] = Query(None)):
    """Return the consolidated `quiz_results.json`. Requires `token` query param matching SECRET_KEY."""
    try:
        if token != SECRET_KEY:
            return JSONResponse({"error": "unauthorized"}, status_code=403)
        out_file = os.path.join(BASE_DIR, "quiz_results.json")
        if not os.path.exists(out_file):
            return JSONResponse({"error": "no_results"}, status_code=404)
        with open(out_file, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return JSONResponse({"results": data})
    except Exception:
        log_error(f"download_results() crash: {traceback.format_exc()}")
        return JSONResponse({"error": "failed"}, status_code=500)

@app.get("/debug/session", response_class=JSONResponse)
async def debug_session(request: Request):
    return JSONResponse({
        "session_profile": get_session_profile(request),
        "session_metrics": get_session_metrics(request)
    })

@app.get("/debug/system", response_class=JSONResponse)
async def debug_system():
    return JSONResponse(dump_debug_state())

# ============================================================
# Astrology helper
# ============================================================
@app.get("/astrology/{birthdate}", response_class=JSONResponse)
async def get_astrology(birthdate: str):
    try:
        zodiac, element = analyze_zodiac(birthdate)
        return JSONResponse({"zodiac": zodiac, "element": element, "hint": astrology_hint(element)})
    except Exception:
        log_error(f"get_astrology() crash: {traceback.format_exc()}")
        return JSONResponse({"zodiac": "Unknown", "element": "Void", "hint": ""})

# ============================================================
# Reset + Admin question injector
# ============================================================
@app.get("/reset", response_class=JSONResponse)
async def reset_session(request: Request):
    clear_session_profile(request)
    request.session.pop("last_fortune", None)
    return JSONResponse({"message": "Session cleared."})

@app.post("/admin/add_question", response_class=JSONResponse)
async def add_question(request: Request):
    try:
        payload = await request.json()
        quiz_engine.add_question(payload)
        quiz_engine.save_question_bank()
        return JSONResponse({"status": "ok", "added": payload})
    except Exception:
        log_error(f"add_question() crash: {traceback.format_exc()}")
        return JSONResponse({"error": "Failed to add question."}, status_code=500)

@app.get("/admin/reload_questions", response_class=JSONResponse)
async def reload_questions():
    try:
        quiz_engine.load_question_bank()
        return JSONResponse({"status": "reloaded", "count": quiz_engine.question_count})
    except Exception:
        log_error(f"reload_questions() crash: {traceback.format_exc()}")
        return JSONResponse({"status": "failed"})

# ============================================================
# Startup / Shutdown
# ============================================================
@app.on_event("startup")
async def startup_event():
    log_debug("Mirror Mirror backend starting...")
    # Defensive: try multiple DB init strategies
    try:
        if hasattr(db, "initialize_tables"):
            db.initialize_tables()
        elif hasattr(db, "init_db"):
            db.init_db()
        else:
            log_debug("DB handler does not expose initialize_tables/init_db — skipping explicit init.")
    except Exception:
        log_error(f"DB init failed: {traceback.format_exc()}")

    # Load the question bank (QuizEngine loads file if provided)
    try:
        quiz_engine.load_question_bank()
        log_debug(f"Loaded question bank: {getattr(quiz_engine, 'question_count', 'unknown')} questions")
    except Exception:
        log_error(f"quiz_engine load failed: {traceback.format_exc()}")

    log_debug("Initialization complete.")

@app.on_event("shutdown")
async def shutdown_event():
    log_debug("Mirror Mirror backend shutting down...")

# ============================================================
# Error handlers (kept simple)
# ============================================================
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    # Keep a helpful JSON response for missing endpoints
    return JSONResponse({"error": f"Endpoint not found: {request.url.path}"}, status_code=404)

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    log_error(f"500 error on {request.method} {request.url.path}: {traceback.format_exc()}")
    return JSONResponse({"error": "Internal server error"}, status_code=500)

# End of file
