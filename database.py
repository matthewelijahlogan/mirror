# database.py
# ======================
# DatabaseHandler aligned to the NEW flat-question format
# Categories now are:
# emotion, focus, intuition, trust, reflection

import sqlite3
from pathlib import Path
from datetime import date

class DatabaseHandler:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None

    def connect(self):
        self.conn = sqlite3.connect(self.db_path, timeout=5)
        self.conn.row_factory = sqlite3.Row
        return self.conn

    def close(self):
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None

    # -------------------------------------------------
    # CREATE TABLES (updated to correct categories)
    # -------------------------------------------------
    def initialize_tables(self):
        conn = self.connect()
        c = conn.cursor()

        # Users
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                birthdate TEXT,
                zodiac TEXT,
                element TEXT
            )
        """)

        # Quiz responses (UPDATED)
        c.execute("""
            CREATE TABLE IF NOT EXISTS quiz_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                date TEXT,
                emotion INTEGER,
                focus INTEGER,
                intuition INTEGER,
                trust INTEGER,
                reflection INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        # Fortunes
        c.execute("""
            CREATE TABLE IF NOT EXISTS fortunes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                date TEXT,
                fortune TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        conn.commit()
        # Ensure migrations: add missing columns to quiz_responses if DB pre-exists with older schema
        try:
            c.execute("PRAGMA table_info(quiz_responses)")
            existing = {row[1] for row in c.fetchall()}  # row[1] is column name
            needed = {"emotion", "focus", "intuition", "trust", "reflection"}
            to_add = needed - existing
            for col in to_add:
                try:
                    c.execute(f"ALTER TABLE quiz_responses ADD COLUMN {col} INTEGER DEFAULT 0")
                except Exception:
                    pass
            conn.commit()
        except Exception:
            pass

        self.close()

    # -------------------------------------------------
    # SAVE RESULT (UPDATED categories)
    # -------------------------------------------------
    def save_user_result(self, name, birthdate, profile: dict, fortune_text: str):
        conn = self.connect()
        c = conn.cursor()

        # Zodiac
        from astrology import analyze_zodiac
        zodiac, element = analyze_zodiac(birthdate)

        # Insert or fetch user
        c.execute("SELECT id FROM users WHERE name=?", (name,))
        row = c.fetchone()
        if row:
            user_id = row["id"]
        else:
            c.execute(
                "INSERT INTO users (name, birthdate, zodiac, element) VALUES (?, ?, ?, ?)",
                (name, birthdate, zodiac, element)
            )
            user_id = c.lastrowid

        # Insert quiz response (UPDATED)
        try:
            c.execute("""
                INSERT INTO quiz_responses
                (user_id, date, emotion, focus, intuition, trust, reflection)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                date.today().isoformat(),
                int(profile.get("emotion", 0)),
                int(profile.get("focus", 0)),
                int(profile.get("intuition", 0)),
                int(profile.get("trust", 0)),
                int(profile.get("reflection", 0))
            ))
        except Exception as e:
            # Fallback: older DB schema — store profile as JSON in a safe fallback table
            try:
                c.execute("""
                    CREATE TABLE IF NOT EXISTS quiz_responses_json (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        date TEXT,
                        profile_json TEXT,
                        FOREIGN KEY(user_id) REFERENCES users(id)
                    )
                """)
                c.execute(
                    "INSERT INTO quiz_responses_json (user_id, date, profile_json) VALUES (?, ?, ?)",
                    (user_id, date.today().isoformat(), json.dumps(profile))
                )
            except Exception:
                # Last resort: ignore saving quiz responses but continue with fortunes
                pass

        # Insert fortune
        c.execute("""
            INSERT INTO fortunes (user_id, date, fortune)
            VALUES (?, ?, ?)
        """, (
            user_id,
            date.today().isoformat(),
            fortune_text
        ))

        conn.commit()
        self.close()

    # -------------------------------------------------
    # USER HISTORY
    # -------------------------------------------------
    def get_user_history(self, username: str):
        conn = self.connect()
        c = conn.cursor()

        # Fetch user ID
        c.execute("SELECT id FROM users WHERE name=?", (username,))
        row = c.fetchone()
        if not row:
            self.close()
            return []

        user_id = row["id"]

        # UPDATED fields
        c.execute("""
            SELECT date, emotion, focus, intuition, trust, reflection
            FROM quiz_responses
            WHERE user_id=?
            ORDER BY date DESC
        """, (user_id,))

        rows = [dict(r) for r in c.fetchall()]
        self.close()
        return rows
