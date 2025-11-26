# quiz_logic.py — expanded edition
# Interprets quiz results and generates enriched personality hints.
# Features:
# - ML-ready feature vector
# - Detailed scoring
# - Historical logging
# - Weighted analysis
# - QuizEngine class for main.py integration
# - Robust loading for multiple questions.json shapes
# - Normalization to flat list, safe-save, debug output

import random
from typing import Dict, List, Any
from datetime import datetime
import json
import os

# ---------------------
# Utility helpers
# ---------------------
def _debug(msg: str):
    """Lightweight debug printing; toggle by setting this to False if noisy"""
    try:
        print(f"[quiz_logic DEBUG {datetime.now().isoformat()}] {msg}")
    except Exception:
        pass

def _is_grouped_questions(obj: Any) -> bool:
    """Detects grouped shape like { "emotion": ["q1", "q2"], "focus": ["q1","q2"] }"""
    if not isinstance(obj, dict):
        return False
    for k, v in obj.items():
        if not isinstance(v, list):
            return False
    return True

def _is_enveloped_questions(obj: Any) -> bool:
    """Detects envelope shape like { "questions": [ ... ] }"""
    return isinstance(obj, dict) and "questions" in obj and isinstance(obj["questions"], list)

def _normalize_grouped_to_list(grouped: Dict[str, List[str]]) -> List[Dict]:
    """Turn grouped format into flat list"""
    out = []
    next_id = 1
    for cat, items in grouped.items():
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict):
                text = item.get("text") or item.get("question") or ""
                qid = item.get("id") or next_id
                choices = item.get("choices")
                out.append({"id": int(qid), "category": cat, "text": text, "choices": choices} if choices else {"id": int(qid), "category": cat, "text": text})
                next_id = max(next_id, int(qid) + 1)
            else:
                out.append({"id": next_id, "category": cat, "text": str(item)})
                next_id += 1
    return out

def _normalize_enveloped_to_list(enveloped: Dict[str, Any]) -> List[Dict]:
    """If envelope like {'questions': [ ... ]} and items may be strings or dicts."""
    raw = enveloped.get("questions", [])
    out = []
    next_id = 1
    for q in raw:
        if isinstance(q, str):
            out.append({"id": next_id, "category": "general", "text": q})
            next_id += 1
        elif isinstance(q, dict):
            qid = q.get("id") or q.get("qid") or next_id
            category = q.get("category") or q.get("trait") or "general"
            text = q.get("text") or q.get("question") or ""
            choices = q.get("choices")
            entry = {"id": int(qid), "category": category, "text": text}
            if choices:
                entry["choices"] = choices
            out.append(entry)
            next_id = max(next_id, int(qid) + 1)
        else:
            out.append({"id": next_id, "category": "general", "text": str(q)})
            next_id += 1
    return out

def _normalize_flat_list(raw_list: List[Any]) -> List[Dict]:
    """Ensure each element is a dict with id, category, text."""
    out = []
    next_id = 1
    for item in raw_list:
        if isinstance(item, dict):
            qid = item.get("id") or item.get("qid") or next_id
            category = item.get("category") or item.get("trait") or item.get("group") or "general"
            text = item.get("text") or item.get("question") or ""
            choices = item.get("choices")
            entry = {"id": int(qid), "category": category, "text": text}
            if choices:
                entry["choices"] = choices
            out.append(entry)
            next_id = max(next_id, int(qid) + 1)
        else:
            out.append({"id": next_id, "category": "general", "text": str(item)})
            next_id += 1
    return out

# ======================
# QuizEngine Class
# ======================
class QuizEngine:
    def __init__(self, question_file: str = None):
        self.question_file = question_file
        self.question_bank: List[Dict] = []
        self.question_count = 0
        if question_file:
            self.load_question_bank()

    def load_question_bank(self):
        """Load questions from JSON file; support multiple shapes and normalize to flat list."""
        try:
            if not self.question_file:
                _debug("No question_file provided to QuizEngine.")
                self.question_bank = []
                self.question_count = 0
                return

            if not os.path.exists(self.question_file):
                _debug(f"Question file not found: {self.question_file}")
                alt = os.path.join(os.path.dirname(self.question_file), "static", "data", "question.json")
                if os.path.exists(alt):
                    self.question_file = alt
                    _debug(f"Using fallback question file at {alt}")
                else:
                    self.question_bank = []
                    self.question_count = 0
                    return

            with open(self.question_file, "r", encoding="utf-8") as f:
                raw = json.load(f)

            if _is_grouped_questions(raw):
                _debug("Detected grouped question object — normalizing to flat list.")
                normalized = _normalize_grouped_to_list(raw)
            elif _is_enveloped_questions(raw):
                _debug("Detected enveloped questions (questions key) — normalizing to flat list.")
                normalized = _normalize_enveloped_to_list(raw)
            elif isinstance(raw, list):
                _debug("Detected flat list — normalizing entries.")
                normalized = _normalize_flat_list(raw)
            elif isinstance(raw, dict) and "questions" not in raw:
                _debug("Top-level dict with non-enveloped format — attempting grouped normalization.")
                normalized = _normalize_grouped_to_list(raw)
            else:
                _debug("Unknown question file shape — attempting safe fallback.")
                normalized = []

            # Ensure unique ids
            used_ids = set()
            for i, q in enumerate(normalized):
                if not isinstance(q, dict):
                    normalized[i] = {"id": i+1, "category": "general", "text": str(q)}
                else:
                    if "id" not in q or q["id"] is None:
                        q["id"] = i+1
                    try:
                        q["id"] = int(q["id"])
                    except Exception:
                        q["id"] = i+1
                    if q["id"] in used_ids:
                        new_id = max(used_ids) + 1 if used_ids else (i+1)
                        q["id"] = new_id
                    used_ids.add(q["id"])
                    q.setdefault("category", q.get("category", "general"))
                    q.setdefault("text", q.get("text", ""))

            normalized.sort(key=lambda x: x.get("id", 0))
            self.question_bank = normalized
            self.question_count = len(self.question_bank)
            _debug(f"Loaded {self.question_count} questions from {self.question_file}")
        except Exception as e:
            print(f"[QuizEngine] Failed to load questions: {e}")
            _debug(f"Exception traceback suppressed for brevity.")
            self.question_bank = []
            self.question_count = 0

    def get_randomized_questions(self, n: int = 6) -> List[Dict]:
        if not self.question_bank:
            _debug("Question bank empty — returning empty list.")
            return []
        n = max(1, min(n, len(self.question_bank)))
        sample = random.sample(self.question_bank, n)
        return [dict(q) for q in sample]

    def add_question(self, question: Dict):
        try:
            if not isinstance(question, dict):
                q_text = str(question)
                new_id = (max([q.get("id", 0) for q in self.question_bank]) + 1) if self.question_bank else 1
                question = {"id": new_id, "category": "general", "text": q_text}

            if "id" not in question or question["id"] is None:
                question["id"] = (max([q.get("id", 0) for q in self.question_bank]) + 1) if self.question_bank else 1
            else:
                try:
                    question["id"] = int(question["id"])
                except Exception:
                    question["id"] = (max([q.get("id", 0) for q in self.question_bank]) + 1) if self.question_bank else 1

            existing_ids = {q.get("id") for q in self.question_bank}
            if question["id"] in existing_ids:
                question["id"] = max(existing_ids) + 1

            question.setdefault("category", question.get("category", "general"))
            question.setdefault("text", question.get("text", ""))

            self.question_bank.append({"id": int(question["id"]), "category": question["category"], "text": question["text"], **({"choices": question["choices"]} if "choices" in question else {})})
            self.question_count = len(self.question_bank)
            _debug(f"Added question id={question['id']} category={question['category']!r}")
        except Exception as e:
            print(f"[QuizEngine] add_question failed: {e}")

    def save_question_bank(self):
        if not self.question_file:
            _debug("No question_file set; skipping save.")
            return
        try:
            to_write = []
            for q in self.question_bank:
                entry = {"id": int(q.get("id", 0)), "category": q.get("category", "general"), "text": q.get("text", "")}
                if "choices" in q and q["choices"] is not None:
                    entry["choices"] = q["choices"]
                to_write.append(entry)

            with open(self.question_file, "w", encoding="utf-8") as f:
                json.dump(to_write, f, indent=2, ensure_ascii=False)
            _debug(f"Question bank saved ({len(to_write)} items) to {self.question_file}.")
        except Exception as e:
            print(f"[QuizEngine] Failed to save question bank: {e}")

    def generate_followup_questions(self, profile: dict = None, n: int = 3) -> List[Dict]:
        """Generate simple follow-up/reflection questions based on a provided profile.
        This is a lightweight, rule-based generator to create more personal questions.
        """
        profile = profile or {}
        out = []
        next_id = (max([q.get('id', 0) for q in self.question_bank]) + 1) if self.question_bank else 1

        # If profile contains numeric answers like q_1: 4, use them
        try:
            # pick top 2 traits by numeric value if available
            numeric_pairs = [(k, int(v)) for k, v in profile.items() if (isinstance(v, int) or (isinstance(v, str) and v.isdigit()))]
            numeric_pairs.sort(key=lambda kv: kv[1], reverse=True)
        except Exception:
            numeric_pairs = []

        # Use process_quiz to get richer hints if available
        templates = []
        try:
            if numeric_pairs and hasattr(self, 'question_bank'):
                # If we have numeric trait keys like 'mood' or q_*, craft personal prompts
                for k, v in numeric_pairs[:2]:
                    trait = k.replace('q_', '')
                    templates.append(f"You rated {trait} highly. Tell a short story when this showed up recently.")
                    templates.append(f"How might you support {trait} more often in daily life?")
            # Attempt to call process_quiz to get hints if present in module
            try:
                from quiz_logic import process_quiz
                hints = process_quiz(**({k: str(v) for k, v in profile.items() if isinstance(v, (int, str))}))
                if isinstance(hints, dict):
                    # create questions based on a few hint keys
                    if 'message' in hints:
                        templates.append(f"You received this message: '{hints['message']}'. What does it mean to you now?")
                    if 'spirit_symbol' in hints:
                        templates.append(f"Your spirit symbol is {hints['spirit_symbol']}. Why does this image matter to you?")
            except Exception:
                # process_quiz may not be importable in some contexts — ignore
                pass

            # fallback generic prompts
            templates.extend([
                "Describe a small ritual that helps you reset.",
                "When did you last feel most like yourself? Describe briefly.",
                "What would you like to explore more deeply about yourself right now?"
            ])

        except Exception:
            templates = [
                "Describe a small ritual that helps you reset.",
                "When did you last feel most like yourself? Describe briefly.",
                "What would you like to explore more deeply about yourself right now?"
            ]

        # Build n questions
        for i in range(n):
            qtext = templates[i % len(templates)]
            out.append({"id": next_id + i, "category": "followup", "text": qtext})
        return out

# ======================
# Quiz Processing Functions
# ======================

def process_quiz(mood: str = "neutral",
                 focus: str = "blurred",
                 trust: str = "low",
                 creativity: str = "moderate",
                 patience: str = "medium",
                 empathy: str = "medium") -> Dict[str, str]:

    mood = (mood or "neutral").lower()
    focus = (focus or "blurred").lower()
    trust = (trust or "low").lower()
    creativity = (creativity or "moderate").lower()
    patience = (patience or "medium").lower()
    empathy = (empathy or "medium").lower()

    energy_map = {
        "calm": "Reflective energy, steady and wise.",
        "excited": "Radiant energy, bold and eager.",
        "neutral": "Balanced energy, quietly powerful.",
        "anxious": "Turbulent energy seeking clarity.",
        "focused": "Directed energy, cutting through distractions."
    }

    clarity_map = {
        "clear": "Your focus cuts through illusions.",
        "blurred": "You are learning to see the unseen.",
        "wandering": "Your thoughts drift like clouds.",
        "sharp": "Perception is acute; details are vivid.",
        "distracted": "Eyes wander, but insight still forms."
    }

    trust_map = {
        "high": "Your heart opens easily to connection.",
        "low": "You guard your truth like a sacred flame.",
        "medium": "You balance faith with careful observation.",
        "skeptical": "Doubt guides your learning, wisely.",
        "forgiving": "Even past wounds teach grace."
    }

    creativity_map = {
        "low": "Innovation simmers quietly within.",
        "moderate": "You weave ideas with ease.",
        "high": "A torrent of imagination flows through you.",
        "latent": "Hidden sparks of brilliance await discovery."
    }

    patience_map = {
        "low": "Action moves faster than thought.",
        "medium": "You balance urgency with deliberation.",
        "high": "Time bends around your calm resolve."
    }

    empathy_map = {
        "low": "Observation over feeling guides you.",
        "medium": "You connect meaningfully, when prompted.",
        "high": "Hearts open wherever you tread."
    }

    spirit_symbols = [
        ("Flame", "Ignites insight and courage."),
        ("Wave", "Flows with change and intuition."),
        ("Leaf", "Grounded growth and resilience."),
        ("Wind", "Brings movement and new perspectives."),
        ("Stone", "Steadfast, patient, and enduring."),
        ("Star", "Illuminates hidden paths."),
        ("Petal", "Gentle beauty and unfolding potential."),
        ("Moon", "Cycles of reflection and emotion.")
    ]
    spirit_symbol, spirit_desc = random.choice(spirit_symbols)

    hints = {
        "energy": energy_map.get(mood, "An undefined aura surrounds you."),
        "clarity": clarity_map.get(focus, "Your inner lens adjusts to truth."),
        "trust": trust_map.get(trust, "Trust flows with your intuition."),
        "creativity": creativity_map.get(creativity, "Ideas await their time to blossom."),
        "patience": patience_map.get(patience, "Time flows according to your pace."),
        "empathy": empathy_map.get(empathy, "Feelings ripple along your path."),
        "spirit_symbol": spirit_symbol,
        "spirit_description": spirit_desc,
        "message": generate_insight_message(mood, focus, trust, creativity, patience, empathy)
    }

    hints["trait_scores"] = compute_trait_scores(mood, focus, trust, creativity, patience, empathy)
    hints["ml_vector"] = generate_ml_vector(hints)

    return hints

# --------------------- Helpers ---------------------

def generate_insight_message(mood: str, focus: str, trust: str,
                             creativity: str, patience: str, empathy: str) -> str:
    templates = [
        "Your inner {mood} guides how you perceive the world.",
        "Balance {focus} with your natural {creativity}.",
        "A mix of {trust} and {empathy} shapes your choices today.",
        "Patience {patience} allows your insights to flourish.",
        "Flow with {creativity} and observe how {clarity} emerges."
    ]
    template = random.choice(templates)
    return template.format(
        mood=mood,
        focus=focus,
        trust=trust,
        creativity=creativity,
        patience=patience,
        empathy=empathy,
        clarity=focus
    )

def compute_trait_scores(mood: str, focus: str, trust: str,
                         creativity: str, patience: str, empathy: str) -> Dict[str, int]:
    score_map = {
        "low": 1, "medium": 3, "moderate": 3, "high": 5,
        "calm": 3, "neutral": 3, "excited": 4,
        "wandering": 2, "clear": 5, "focused": 5, "sharp": 5, "distracted": 2,
        "skeptical": 2, "forgiving": 4, "latent": 2, "anxious": 2
    }
    scores = {}
    for trait, val in [("mood", mood), ("focus", focus), ("trust", trust),
                       ("creativity", creativity), ("patience", patience), ("empathy", empathy)]:
        scores[trait] = score_map.get(val, 3)
    return scores

def summarize_traits(hints: Dict[str, str]) -> str:
    return (f"Energy: {hints.get('energy')} | "
            f"Clarity: {hints.get('clarity')} | "
            f"Trust: {hints.get('trust')} | "
            f"Creativity: {hints.get('creativity')} | "
            f"Patience: {hints.get('patience')} | "
            f"Empathy: {hints.get('empathy')} | "
            f"Symbol: {hints.get('spirit_symbol')} ({hints.get('spirit_description')})")

def randomize_quiz_traits(traits: List[str] = None) -> Dict[str, str]:
    options = {
        "mood": ["calm", "neutral", "excited", "anxious", "focused"],
        "focus": ["clear", "blurred", "wandering", "sharp", "distracted"],
        "trust": ["high", "medium", "low", "skeptical", "forgiving"],
        "creativity": ["low", "moderate", "high", "latent"],
        "patience": ["low", "medium", "high"],
        "empathy": ["low", "medium", "high"]
    }
    traits = traits or list(options.keys())
    return {t: random.choice(options[t]) for t in traits}

# ======================
# ML + Analytics Enhancements
# ======================
def generate_ml_vector(hints: Dict[str, str]) -> Dict[str, int]:
    vector = hints.get("trait_scores", {}).copy()
    vector["spirit_symbol_id"] = hash(hints.get("spirit_symbol", "")) % 100
    return vector

def save_ml_record(hints: Dict[str, str], filepath: str = "ml_training.json"):
    record = hints.get("ml_vector", {}).copy()
    record["timestamp"] = datetime.now().isoformat()
    try:
        data = []
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        data.append(record)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[quiz_logic] Failed to save ML record: {e}")

# ======================
# Module Test
# ======================
if __name__ == "__main__":
    # Simple manual module test
    demo_answers = randomize_quiz_traits()
    print("Random demo answers:", demo_answers)
    try:
        res = process_quiz(
            mood=demo_answers.get('mood', 'neutral'),
            focus=demo_answers.get('focus', 'blurred'),
            trust=demo_answers.get('trust', 'medium'),
            creativity=demo_answers.get('creativity', 'moderate'),
            patience=demo_answers.get('patience', 'medium'),
            empathy=demo_answers.get('empathy', 'medium')
        )
        print("\n--- Reflection Result ---")
        print(json.dumps(res, indent=2))
    except Exception as e:
        print(f"Demo run failed: {e}")

