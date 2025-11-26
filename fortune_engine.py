"""
fortune_engine.py

Robust ML + rule-based fortune engine (additive/expanded).

Design goals:
- Keep original behavior: rule-based fortune + optional ML gen (distilgpt2)
- Lazy-load transformers so project runs when 'transformers' isn't installed
- Provide robust persistence for per-user memory/history
- Add analytics and export helpers for debugging and improving fortunes
- Defensive error handling and optional verbose debug logging
- Many small helpers to keep expanding without removing original code

Note:
- If you plan to run the ML path on-device (phone), make sure the device
  supports the required libraries and has sufficient memory. The code will
  gracefully fall back to rule-based generation if transformers are missing.
"""

# Standard library
import os
import json
import random
import traceback
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from collections import Counter

# Local configuration (change as needed)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_FILE = os.path.join(BASE_DIR, "mirror_memory.json")
MODEL_NAME = "distilgpt2"   # small-ish GPT-2 derivative; replace if you choose a different small model
KEEP_HISTORY = 12           # keep last N fortunes for each user
MAX_PROMPT_TOKENS = 3000    # token cap for prompts (safety)
MAX_NEW_TOKENS = 180        # how many new tokens to generate when using ML
DEBUG_MODE = False          # flip to True for verbose console logging

# Optional ML backend: lazy import
# IMPORTANT: Set FORCE_RULE_BASED = True to disable ML entirely and use rule-based fallback only
FORCE_RULE_BASED = True  # Set to False to enable ML fortune generation
try:
    from transformers import GPT2LMHeadModel, GPT2TokenizerFast
    TRANSFORMERS_AVAILABLE = True and not FORCE_RULE_BASED
except Exception:
    TRANSFORMERS_AVAILABLE = False

# Internal model/tokenizer (populated lazily by init_model)
_model = None
_tokenizer = None

# ================================
# Utility / Logging
# ================================

def debug_log(*args, **kwargs):
    """Conditional debug printing — use DEBUG_MODE to toggle verbosity."""
    if DEBUG_MODE:
        now = datetime.now().isoformat()
        print(f"[fortune_engine DEBUG {now}]", *args, **kwargs)

def safe_load_json(path: str) -> Dict[str, Any]:
    """Load JSON safely; return empty dict on failure."""
    try:
        if not os.path.exists(path):
            debug_log(f"safe_load_json: file not found: {path}")
            return {}
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            debug_log(f"safe_load_json: loaded {len(data)} top-level keys from {path}")
            return data
    except Exception as e:
        print(f"[fortune_engine] safe_load_json error for {path}: {e}")
        debug_log(traceback.format_exc())
        return {}

def safe_write_json(path: str, data: Dict[str, Any]) -> bool:
    """Write JSON safely: write to temp file and atomic-rename. Returns True on success."""
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
        debug_log(f"safe_write_json: wrote {len(data)} top-level keys to {path}")
        return True
    except Exception as e:
        print(f"[fortune_engine] safe_write_json error for {path}: {e}")
        debug_log(traceback.format_exc())
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
        return False

# ================================
# Memory: load / save / append
# ================================

def load_memory() -> Dict[str, List[Dict[str, Any]]]:
    """Load the mirror memory (per-user fortunes)."""
    mem = safe_load_json(MEMORY_FILE)
    if not isinstance(mem, dict):
        debug_log("load_memory: memory file root not dict — resetting.")
        mem = {}
    return mem

def save_memory(mem: Dict[str, List[Dict[str, Any]]]) -> bool:
    """Persist memory to disk."""
    return safe_write_json(MEMORY_FILE, mem)

def append_memory_entry(name: str, fortune_text: str, zodiac: str, tone: str, theme: Optional[str]=None) -> None:
    """Append an entry to the user's fortune history and persist."""
    try:
        mem = load_memory()
        history = mem.get(name, [])
        entry = {
            "timestamp": datetime.now().isoformat(),
            "fortune": fortune_text,
            "zodiac": zodiac,
            "tone": tone,
            "theme": theme or guess_theme_from_text(fortune_text)
        }
        history.append(entry)
        mem[name] = history[-KEEP_HISTORY:]
        save_memory(mem)
        debug_log(f"append_memory_entry: appended entry for {name}; history length now {len(mem[name])}")
    except Exception as e:
        print(f"[fortune_engine] append_memory_entry failed: {e}")
        debug_log(traceback.format_exc())

def get_user_history(name: str) -> List[Dict[str, Any]]:
    """Return history list for name (empty list if not found)."""
    mem = load_memory()
    return mem.get(name, [])

# ================================
# Astrology helpers
# ================================

def analyze_zodiac(birthdate: str) -> Tuple[str, str]:
    """Return zodiac sign and element given a birthdate string (ISO-like)."""
    try:
        parts = birthdate.split("-")
        if len(parts) < 3:
            debug_log("analyze_zodiac: invalid birthdate format", birthdate)
            return "Unknown", "Void"
        month = int(parts[1]); day = int(parts[2])
    except Exception:
        debug_log("analyze_zodiac: parse failed for", birthdate)
        return "Unknown", "Void"

    signs = [
        ((1,20,2,18), "Aquarius", "Air"),
        ((2,19,3,20), "Pisces", "Water"),
        ((3,21,4,19), "Aries", "Fire"),
        ((4,20,5,20), "Taurus", "Earth"),
        ((5,21,6,20), "Gemini", "Air"),
        ((6,21,7,22), "Cancer", "Water"),
        ((7,23,8,22), "Leo", "Fire"),
        ((8,23,9,22), "Virgo", "Earth"),
        ((9,23,10,22), "Libra", "Air"),
        ((10,23,11,21), "Scorpio", "Water"),
        ((11,22,12,21), "Sagittarius", "Fire"),
        ((12,22,1,19), "Capricorn", "Earth")
    ]
    for (m1,d1,m2,d2), sign, element in signs:
        if (month == m1 and day >= d1) or (month == m2 and day <= d2):
            return sign, element
    return "Unknown", "Void"

def astrology_hint(element: str) -> str:
    """Return a short astrology-inspired hint string for an element."""
    hints = {
        "Fire": "your passion lights hidden crossroads.",
        "Water": "your intuition echoes in quiet pools.",
        "Air": "your thoughts drift toward new horizons.",
        "Earth": "your steps root change into practice.",
        "Void": "the cosmos watches without shape."
    }
    return hints.get(element, "")

# ================================
# Personality signature computation
# ================================

def compute_personality_signature(profile: Dict[str, Any]) -> Tuple[str, str]:
    """
    Derive a tone and dominant trait from the numeric traits in profile.
    Profile is expected to be a mapping of trait -> numeric or numeric-like string.
    Returns: (tone, dominant_trait)
    """
    if not profile or not isinstance(profile, dict):
        return "neutral", "unknown"
    vals = []
    numeric_map = {}
    for k, v in profile.items():
        try:
            fv = float(v)
            vals.append(fv)
            numeric_map[k] = fv
        except Exception:
            # skip non-numeric (but leave available for ML prompt)
            continue
    if not vals:
        return "neutral", "unknown"
    avg = sum(vals) / len(vals)
    if avg >= 4.2:
        tone = "bright"
    elif avg >= 2.6:
        tone = "neutral"
    else:
        tone = "dark"

    try:
        dominant = max(numeric_map.keys(), key=lambda k: numeric_map[k])
    except Exception:
        dominant = list(profile.keys())[0] if profile else "unknown"
    debug_log(f"compute_personality_signature: avg={avg:.2f}, tone={tone}, dominant={dominant}")
    return tone, dominant

def temporal_tone_adjust(tone: str) -> str:
    """Slightly shift the tone by the hour of the day to give varied fortunes."""
    h = datetime.now().hour
    if 22 <= h or h <= 5:
        if tone == "bright":
            return "neutral"
        if tone == "neutral":
            return "dark"
    if 6 <= h <= 10 and tone == "dark":
        return "neutral"
    return tone

# ================================
# Rule-based composer (fallback)
# ================================

# Expand vocabulary with many entries so the file is more robust
VOCAB = {
    "themes": [
        "reflection","destiny","memory","light","shadow","echo","flux","grace",
        "illusion","time","horizon","truth","dream","origin","stillness","threshold",
        "tide","constellation","pulse","garden"
    ],
    "adjectives": [
        "celestial","velvet","haunting","luminous","ashen","resonant",
        "ancient","radiant","forgotten","opalescent","gilded","nocturnal",
        "transcendent","serpentine","quiet"
    ],
    "tones": {
        "bright": [
            "A golden light crowns your choices today.",
            "The mirror smiles upon this turning of the page.",
            "New paths unfold just beyond your steady step."
        ],
        "neutral": [
            "Balance lingers at the glass; take another breath.",
            "A quiet clarity ripples beneath your surface.",
            "Consider the space between intent and action."
        ],
        "dark": [
            "Shadows stir where the mirror does not reach.",
            "A hush warns: not all reflections are truth.",
            "Tread with curiosity and measured caution tonight."
        ]
    },
    "omens": [
        "a bird's wing caught in the current of morning",
        "the scent of rain on ancient stone",
        "a laugh from a stranger who knows your secret",
        "a folded note you've not yet found",
        "a glint that isn't yours"
    ]
}

def guess_theme_from_text(text: str) -> str:
    """Heuristic to pick a theme from a piece of text; naive but useful."""
    text_low = (text or "").lower()
    counts = {}
    for t in VOCAB["themes"]:
        counts[t] = text_low.count(t)
    # fallback to random theme if none obvious
    top = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    if top and top[0][1] > 0:
        return top[0][0]
    return random.choice(VOCAB["themes"])

def rule_based_fortune(name: str, zodiac: str, element: str, tone: str, dominant: str, history: List[Dict[str, Any]]) -> str:
    """
    Compose a rule-based poetic fortune using vocabulary and simple heuristics.
    Returns the fortune string.
    """
    theme = random.choice(VOCAB["themes"])
    adj = random.choice(VOCAB["adjectives"])
    omen = random.choice(VOCAB["omens"])
    tone = temporal_tone_adjust(tone)
    tone_line = random.choice(VOCAB["tones"].get(tone, VOCAB["tones"]["neutral"]))
    memory_hint = ""
    if history:
        try:
            last_theme = history[-1].get("theme", "reflection")
            memory_hint = f"The mirror remembers a past theme of '{last_theme}'."
        except Exception:
            memory_hint = ""
    astro = astrology_hint(element)
    ts = datetime.now().strftime("%B %d, %Y")
    # Construct and return
    fortune = (
        f"🪞 Mirror of {theme.title()} — {ts}\n\n"
        f"{name}, the {adj} child of {zodiac}, {tone_line}\n"
        f"Your {dominant} stirs the current of {theme}, and {astro}\n"
        f"As {omen} passes, listen for the quiet next step.\n\n"
        f"{memory_hint}\n"
        "May your reflection reveal what your eyes do not."
    )
    debug_log("rule_based_fortune composed:", fortune.replace("\n", " | ")[:300])
    return fortune

# ================================
# ML generator (transformers) — robust + defensive
# ================================

def init_model() -> bool:
    """Initialize the model and tokenizer if transformers are available."""
    global _model, _tokenizer
    if not TRANSFORMERS_AVAILABLE:
        debug_log("init_model: transformers package not available")
        return False
    if _model is not None and _tokenizer is not None:
        debug_log("init_model: model already initialized")
        return True
    try:
        debug_log("init_model: loading tokenizer and model:", MODEL_NAME)
        _tokenizer = GPT2TokenizerFast.from_pretrained(MODEL_NAME)
        # Ensure pad token exists
        if _tokenizer.pad_token_id is None:
            debug_log("init_model: pad_token missing — setting pad_token to eos_token")
            _tokenizer.pad_token = _tokenizer.eos_token
        _model = GPT2LMHeadModel.from_pretrained(MODEL_NAME)
        _model.eval()
        debug_log("init_model: model loaded successfully")
        return True
    except Exception as e:
        print("[fortune_engine] Model init failed:", e)
        debug_log(traceback.format_exc())
        _model = None
        _tokenizer = None
        return False

def _truncate_prompt_tokens(input_ids, max_tokens: int):
    """Truncate input token ids to keep at most max_tokens tokens (from the right)."""
    try:
        import torch
        if input_ids.shape[-1] <= max_tokens:
            return input_ids
        return input_ids[:, -max_tokens:]
    except Exception:
        # If torch isn't available or input isn't torch tensor, attempt list-slicing
        try:
            if hasattr(input_ids, "__len__"):
                # assume it's a 1D list
                return input_ids[-max_tokens:]
        except Exception:
            pass
    return input_ids

def generate_ml_fortune(user_profile: Dict[str, Any], max_new_tokens: int = MAX_NEW_TOKENS) -> str:
    """
    Generate a fortune using the transformer model.
    Raises on failure so caller can fallback to rule-based.
    """
    if not init_model():
        raise RuntimeError("Model not available (transformers missing or init failed)")

    name = user_profile.get("name", "Wanderer")
    birth = user_profile.get("birthdate", "1900-01-01")
    zodiac, element = analyze_zodiac(birth)
    # Build profile snippet: include quiz and known keys
    profile_clipped = {k: v for k, v in (user_profile.get("quiz") or user_profile).items() if k not in ("name", "birthdate")}
    tone, dominant = compute_personality_signature(profile_clipped)
    tone = temporal_tone_adjust(tone)
    memory = load_memory()
    history = memory.get(name, [])
    history_text = "\n".join([h.get("fortune", "") for h in history[-5:]]) if history else ""

    prompt = (
        f"You are an artistic poetic oracle. Write a gentle, original fortune for {name}.\n"
        f"Keep it short (1-3 sentences). Use evocative language, and do not repeat past fortunes verbatim.\n"
        f"Zodiac: {zodiac} (element: {element}). Tone: {tone}. Dominant trait: {dominant}.\n"
        f"Profile: {json_snippet(profile_clipped)}\n"
        f"Recent reflections:\n{history_text}\n"
        f"Fortune:"
    )
    debug_log("generate_ml_fortune: prompt length chars:", len(prompt))

    try:
        # Tokenize (returns torch tensors if tokenizer supports it)
        enc = _tokenizer(prompt, return_tensors="pt")
        input_ids = enc.input_ids
        attention_mask = enc.attention_mask

        # Truncate if too long
        input_ids = _truncate_prompt_tokens(input_ids, MAX_PROMPT_TOKENS)
        # adjust attention_mask if tensor shape changed
        if hasattr(attention_mask, "__class__") and hasattr(attention_mask, "shape"):
            attention_mask = attention_mask[:, -input_ids.shape[-1]:]

        # Model generate
        outputs = _model.generate(
            input_ids=input_ids,
            attention_mask=attention_mask,
            pad_token_id=_tokenizer.eos_token_id,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=0.85,
            top_k=50,
            top_p=0.92,
            num_return_sequences=1,
            eos_token_id=_tokenizer.eos_token_id
        )

        raw = _tokenizer.decode(outputs[0], skip_special_tokens=True)
        # Attempt to extract the portion after the prompt
        gen = raw[len(prompt):].strip() if raw.startswith(prompt) else raw.strip()
        gen = clean_generated_text(gen)
        # If cleaning detected junk, raise so caller can fall back to rule-based
        if not gen or not isinstance(gen, str) or len(gen.strip()) < 10:
            raise ValueError(f"cleaned text too short or empty (indicates junk ML output)")
        append_memory_entry(name, gen, zodiac, tone, theme=guess_theme_from_text(gen))
        debug_log("generate_ml_fortune: generated text:", gen)
        return gen
    except Exception as e:
        debug_log("generate_ml_fortune: failure:", traceback.format_exc())
        raise

# ================================
# Helpers & analytics
# ================================

def json_snippet(d: Dict[str, Any], maxlen: int = 240) -> str:
    """Serialize a dict to JSON and truncate to maxlen characters sensibly."""
    try:
        s = json.dumps(d, ensure_ascii=False)
        if len(s) > maxlen:
            # try to cut at a comma boundary
            return s[:maxlen].rsplit(",", 1)[0] + "..."
        return s
    except Exception:
        return "{}"

def clean_generated_text(text: str) -> str:
    """Trim and heuristically shorten generated text (cap sentences). Also reject repetitive junk."""
    t = (text or "").strip()
    if not t:
        return t
    
    # Check for repetitive patterns early
    words = t.split()
    if len(words) > 5:
        word_counts = Counter(words)
        most_common_count = max(word_counts.values()) if word_counts else 0
        # If any word appears in >60% of text, it's junk
        if most_common_count > len(words) * 0.6:
            debug_log(f"clean_generated_text: rejecting repetitive text (word '{max(word_counts, key=word_counts.get)}' appears too often)")
            return ""  # Return empty string to signal invalid
    
    # Prefer first two sentences
    for sep in (".", "?", "!"):
        if sep in t:
            parts = [p.strip() for p in t.split(sep) if p.strip()]
            if len(parts) >= 2:
                return (parts[0] + sep + " " + parts[1] + sep).strip()
            else:
                # only one sentence — return it
                return (parts[0] + sep).strip()
    # fallback to length cap
    return t if len(t) <= 400 else (t[:400].rsplit(" ", 1)[0] + "...")

def summarize_user_history(name: str) -> Dict[str, Any]:
    """Return analytics summary for a user's fortune history."""
    mem = load_memory()
    history = mem.get(name, [])
    if not history:
        return {"count": 0, "most_common_tone": None, "most_common_theme": None, "recent": []}
    # analytics
    tone_counts = {}
    theme_counts = {}
    for h in history:
        tone_counts[h.get("tone", "unknown")] = tone_counts.get(h.get("tone", "unknown"), 0) + 1
        theme_counts[h.get("theme", "reflection")] = theme_counts.get(h.get("theme", "reflection"), 0) + 1
    most_common_tone = max(tone_counts.items(), key=lambda kv: kv[1])[0] if tone_counts else None
    most_common_theme = max(theme_counts.items(), key=lambda kv: kv[1])[0] if theme_counts else None
    return {
        "count": len(history),
        "most_common_tone": most_common_tone,
        "most_common_theme": most_common_theme,
        "recent": history[-5:][::-1]  # newest-first
    }

def export_memory_csv(path: str) -> bool:
    """
    Export the memory to CSV for quick analysis.
    Fields: name,timestamp,zodiac,tone,theme,fortune
    """
    try:
        import csv
        mem = load_memory()
        with open(path, "w", newline='', encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["name", "timestamp", "zodiac", "tone", "theme", "fortune"])
            for name, hist in mem.items():
                for h in hist:
                    writer.writerow([name, h.get("timestamp"), h.get("zodiac"), h.get("tone"), h.get("theme"), h.get("fortune")])
        debug_log("export_memory_csv: exported to", path)
        return True
    except Exception as e:
        print("[fortune_engine] export_memory_csv failed:", e)
        debug_log(traceback.format_exc())
        return False

def purge_memory_older_than(days: int = 365) -> int:
    """Remove memory entries older than given days; returns number of deleted entries."""
    try:
        mem = load_memory()
        cutoff = datetime.now() - timedelta(days=days)
        removed = 0
        for name in list(mem.keys()):
            hist = mem.get(name, [])
            newhist = [h for h in hist if datetime.fromisoformat(h.get("timestamp")) >= cutoff]
            removed += (len(hist) - len(newhist))
            if newhist:
                mem[name] = newhist
            else:
                del mem[name]
        save_memory(mem)
        debug_log(f"purge_memory_older_than: removed {removed} entries older than {days} days")
        return removed
    except Exception as e:
        print("[fortune_engine] purge_memory_older_than failed:", e)
        debug_log(traceback.format_exc())
        return 0

def batch_generate_for_users(user_profiles: Dict[str, Dict[str, Any]], force_rule_based: bool = False) -> Dict[str, str]:
    """
    Batch-generate fortunes for many users. Returns mapping name->fortune.
    This is useful for local testing or seeding a cache.
    """
    results = {}
    for name, profile in user_profiles.items():
        try:
            if force_rule_based:
                zodiac, elem = analyze_zodiac(profile.get("birthdate", "1900-01-01"))
                tone, dom = compute_personality_signature(profile.get("quiz") or {})
                f = rule_based_fortune(name, zodiac, elem, tone, dom, get_user_history(name))
            else:
                f = generate_fortune(profile)
            results[name] = f
        except Exception as e:
            results[name] = f"[error generating fortune: {e}]"
    return results

# ================================
# Public main entry
# ================================

def generate_fortune(user_data: Dict[str, Any]) -> str:
    """
    Primary function called by the application.
    Try ML generation first (if available), otherwise fallback to rule-based composition.
    Guarantees a returning string (no exceptions bubble up).
    """
    try:
        # Normalize user_data shape: if top-level keys exist instead of 'quiz'
        profile = user_data.get("quiz") if isinstance(user_data.get("quiz"), dict) else user_data
        # Attempt ML generation if possible
        if TRANSFORMERS_AVAILABLE:
            try:
                debug_log("generate_fortune: attempting ML generation")
                ml_gen = generate_ml_fortune(user_data)
                # Validate ML output: must be non-empty and not a known placeholder
                def _is_valid(text: Optional[str]) -> bool:
                    if not text or not isinstance(text, str):
                        return False
                    t = text.strip()
                    if len(t) < 10:
                        return False
                    # common malformed outputs to avoid
                    bad_markers = ["unknown (element: void)", "fortune: unknown (element: void)", "the mirror is silent"]
                    low = t.lower()
                    for b in bad_markers:
                        if b in low:
                            return False
                    
                    # Detect repetitive patterns (e.g., "moon, moon, moon..." or "Zodiac: southern, Zodiac: southern...")
                    # Split by common separators and check for high repetition
                    words = t.split()
                    if len(words) > 5:
                        # Count word frequency
                        word_counts = Counter(words)
                        # If any single word appears in >60% of the text, it's likely repetitive junk
                        most_common_count = max(word_counts.values()) if word_counts else 0
                        if most_common_count > len(words) * 0.6:
                            debug_log(f"_is_valid: detected repetitive pattern (word '{max(word_counts, key=word_counts.get)}' appears {most_common_count}/{len(words)} times)")
                            return False
                    
                    return True

                if _is_valid(ml_gen):
                    debug_log("generate_fortune: ML generation succeeded and validated")
                    return ml_gen.strip()
                else:
                    debug_log("generate_fortune: ML generation returned invalid text, falling back")
            except Exception as e:
                # Log and fallback
                print("[fortune_engine] ML generation error:", e)
                debug_log(traceback.format_exc())

        # Rule-based fallback
        name = user_data.get("name", "Wanderer")
        birth = user_data.get("birthdate", "1900-01-01")
        zodiac, element = analyze_zodiac(birth)
        profile_map = user_data.get("quiz") or (user_data if isinstance(user_data, dict) else {})
        tone, dominant = compute_personality_signature(profile_map)
        history = load_memory().get(name, [])
        rule = rule_based_fortune(name, zodiac, element, tone, dominant, history)
        # final sanity: ensure rule isn't a small placeholder
        if not rule or not isinstance(rule, str) or len(rule.strip()) < 20:
            debug_log("generate_fortune: rule-based fortune too short, returning default message")
            fallback = "The mirror is quiet right now. Try again in a little while."
            append_memory_entry(name, fallback, zodiac, tone, theme="quiet")
            return fallback

        debug_log("generate_fortune: returning rule-based fortune")
        append_memory_entry(name, rule, zodiac, tone, theme=guess_theme_from_text(rule))
        return rule
    except Exception:
        debug_log("generate_fortune: unexpected error", traceback.format_exc())
        return "The mirror is quiet right now. Try again in a little while."

# ================================
# Backwards-compatible helpers and aliases
# ================================

def get_user_history_alias(name: str) -> List[Dict[str, Any]]:
    return get_user_history(name)

# Expose some useful functions for main.py to call
__all__ = [
    "generate_fortune",
    "generate_ml_fortune",
    "init_model",
    "load_memory",
    "save_memory",
    "append_memory_entry",
    "get_user_history",
    "summarize_user_history",
    "export_memory_csv",
    "purge_memory_older_than",
    "batch_generate_for_users",
    "compute_personality_signature",
    "analyze_zodiac",
    "astrology_hint"
]

# ================================
# Development / quick test harness
# ================================

if __name__ == "__main__":
    # Quick manual test if run directly
    DEBUG_MODE = True
    print("fortune_engine quick test — DEBUG_MODE ON")
    sample_user = {
        "name": "TestUser",
        "birthdate": "1990-04-21",
        "quiz": {
            "emotion": 4,
            "focus": 3,
            "intuition": 5,
            "trust": 2,
            "reflection": 4
        }
    }
    try:
        # Try ML (if available) but always safe
        if TRANSFORMERS_AVAILABLE:
            print("TRANSFORMERS_AVAILABLE: True — attempting init_model()")
            ok = init_model()
            print("init_model returned:", ok)
        else:
            print("TRANSFORMERS_AVAILABLE: False — ML path disabled")

        fortune = generate_fortune(sample_user)
        print("Generated fortune:\n", fortune)
        print("\nUser history summary:", summarize_user_history(sample_user["name"]))
    except Exception as ex:
        print("[fortune_engine] direct run error:", ex)
        debug_log(traceback.format_exc())

    # Show how to purge old memory (example)
    removed = purge_memory_older_than(3650)  # purge entries older than 10 years as demo
    print(f"purge_memory_older_than returned: {removed}")
