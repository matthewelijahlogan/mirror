# astrology.py
# ======================
# Zodiac analysis + astrology hints
# Fully aligned with main.py

from datetime import datetime

ZODIAC_SIGNS = [
    ("Capricorn", (12, 22), (1, 19)),
    ("Aquarius", (1, 20), (2, 18)),
    ("Pisces", (2, 19), (3, 20)),
    ("Aries", (3, 21), (4, 19)),
    ("Taurus", (4, 20), (5, 20)),
    ("Gemini", (5, 21), (6, 20)),
    ("Cancer", (6, 21), (7, 22)),
    ("Leo", (7, 23), (8, 22)),
    ("Virgo", (8, 23), (9, 22)),
    ("Libra", (9, 23), (10, 22)),
    ("Scorpio", (10, 23), (11, 21)),
    ("Sagittarius", (11, 22), (12, 21))
]

ELEMENTS = {
    "Fire": ["Aries", "Leo", "Sagittarius"],
    "Earth": ["Taurus", "Virgo", "Capricorn"],
    "Air": ["Gemini", "Libra", "Aquarius"],
    "Water": ["Cancer", "Scorpio", "Pisces"]
}

ASTROLOGY_HINTS = {
    "Fire": "You are passionate, energetic, and courageous.",
    "Earth": "You are grounded, practical, and reliable.",
    "Air": "You are intellectual, communicative, and curious.",
    "Water": "You are intuitive, empathetic, and emotional.",
    "Void": "Your star sign is undefined. Unique paths await you."
}


def analyze_zodiac(birthdate_str):
    """Returns (zodiac, element) tuple for a birthdate string YYYY-MM-DD"""
    try:
        date_obj = datetime.strptime(birthdate_str, "%Y-%m-%d")
        for sign, start, end in ZODIAC_SIGNS:
            if (date_obj.month == start[0] and date_obj.day >= start[1]) or \
               (date_obj.month == end[0] and date_obj.day <= end[1]):
                element = get_element(sign)
                return sign, element
        return "Unknown", "Void"
    except Exception:
        return "Unknown", "Void"


def get_element(sign):
    """Returns element type for a zodiac sign"""
    for elem, signs in ELEMENTS.items():
        if sign in signs:
            return elem
    return "Void"


def astrology_hint(element):
    """Returns a descriptive hint for a zodiac element"""
    return ASTROLOGY_HINTS.get(element, ASTROLOGY_HINTS["Void"])
