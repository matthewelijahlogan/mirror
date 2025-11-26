import json
import os
from datetime import datetime
from collections import Counter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY = os.path.join(BASE, 'mirror_memory.json')

if not os.path.exists(MEMORY):
    print('No memory file found at', MEMORY)
    raise SystemExit(1)

bak = MEMORY + '.bak.' + datetime.now().strftime('%Y%m%dT%H%M%S')
print('Backing up', MEMORY, '->', bak)
with open(MEMORY, 'r', encoding='utf-8') as f:
    mem = json.load(f)
with open(bak, 'w', encoding='utf-8') as f:
    json.dump(mem, f, indent=2, ensure_ascii=False)

def is_repetitive_junk(text: str) -> bool:
    """Detect if text is repetitive junk (like 'moon moon moon...' or 'Zodiac: southern, Zodiac: southern...')"""
    if not text or not isinstance(text, str):
        return False
    words = text.split()
    if len(words) < 5:
        return False
    word_counts = Counter(words)
    # Check two things:
    # 1. If any single word appears in >60% of text (obvious repetition)
    # 2. If any word appears more than 5 times in a short text (likely junk)
    most_common_count = max(word_counts.values()) if word_counts else 0
    if most_common_count > len(words) * 0.6:
        return True
    if most_common_count > 5 and len(words) < 50:
        # Short text with a word appearing >5 times is likely junk
        return True
    return False

removed_total = 0
truncated_total = 0
duplicates_total = 0
repetitive_total = 0

cleaned = {}
for name, history in mem.items():
    if not isinstance(history, list):
        cleaned[name] = history
        continue

    seen = set()
    new_hist_rev = []  # we'll build newest-first to prefer recent
    for entry in reversed(history):
        fortune = entry.get('fortune', '') if entry else ''
        if not fortune or not isinstance(fortune, str):
            removed_total += 1
            continue
        low = fortune.lower()
        # skip well-known bad placeholders
        if 'unknown (element: void)' in low or 'the mirror is silent' in low or 'fortune: unknown (element: void)' in low:
            removed_total += 1
            continue
        # skip empty or trivial
        if len(fortune.strip()) < 8:
            removed_total += 1
            continue
        # skip obviously short/corrupted text (< 40 chars and doesn't contain mirror/fortune emoji)
        if len(fortune.strip()) < 40 and '🪞' not in fortune:
            removed_total += 1
            continue
        # skip repetitive junk (e.g., "moon moon moon..." or "Zodiac: southern...")
        if is_repetitive_junk(fortune):
            repetitive_total += 1
            continue
        # truncate extremely long fortunes
        if len(fortune) > 4000:
            entry = dict(entry)
            entry['fortune'] = fortune[:1000].rstrip() + "\n\n(Truncated long fortune)"
            truncated_total += 1
            fortune = entry['fortune']
        # dedupe by exact fortune text
        if fortune in seen:
            duplicates_total += 1
            continue
        seen.add(fortune)
        new_hist_rev.append(entry)
    # restore oldest-first
    cleaned[name] = list(reversed(new_hist_rev))

# write cleaned file
with open(MEMORY, 'w', encoding='utf-8') as f:
    json.dump(cleaned, f, indent=2, ensure_ascii=False)

print('Cleanup complete')
print('Removed placeholder/empty entries:', removed_total)
print('Removed repetitive/junk entries:', repetitive_total)
print('Truncated very long entries:', truncated_total)
print('Removed duplicate entries:', duplicates_total)
print('Backup saved to:', bak)