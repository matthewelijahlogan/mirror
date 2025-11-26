# Mirror Oracle 🔮

A personalized fortune experience powered by FastAPI, featuring a paginated quiz with semantic trait mapping, self-generating follow-up questions, and a rule-based fortune engine.

## Features

- **Profound UI**: Glass-morphism design with fixed overlay titles and smooth animations
- **Paginated Quiz**: One-question-at-a-time flow with back/next navigation and progress tracking
- **Semantic Mapping**: Client-side conversion of numeric slider values to meaningful buckets (low/medium/high)
- **Self-Generating Questions**: Follow-up questions personalized based on user traits and process_quiz hints
- **Mobile-Optimized**: Touch-friendly controls, responsive layout, full mobile support
- **Rule-Based Fortune Engine**: Deterministic fortune generation with validation against repetitive/malformed output
- **Bulk Result Export**: Admin endpoint (`/admin/download_results?token=<SECRET_KEY>`) for exporting consolidated quiz results
- **JSON Persistence**: All quiz results stored in `quiz_results.json` for easy analysis and profile building

## Tech Stack

- **Backend**: FastAPI with Jinja2 templating and SQLite persistence
- **Frontend**: Vanilla JavaScript (no framework) with semantic bucket mapping
- **Styling**: CSS glass-morphism with layered animations and responsive media queries
- **Database**: SQLite with JSON fallback
- **Persistence**: quiz_results.json, mirror_memory.json, ml_training.json

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js (optional, for Cordova builds)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/mirror.git
cd mirror
```

2. Create and activate virtual environment:
```bash
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows PowerShell
# or: source venv/bin/activate  # macOS/Linux
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### Running Locally

```bash
python -m uvicorn main:app --reload --port 8000
```

Open http://localhost:8000 in your browser.

## Usage

### Landing Page
- Click "Begin Quiz" to start the personalized experience

### Quiz Flow
- Answer 6 paginated questions (one per screen)
- Use sliders or choice buttons; values map to semantic buckets (low/medium/high)
- Review your profile and receive a personalized fortune
- Results automatically saved to `quiz_results.json`

### Admin Endpoint
Export all quiz results:
```bash
curl "http://localhost:8000/admin/download_results?token=<your-secret-key>"
```
Replace `<your-secret-key>` with the value of `SECRET_KEY` in `main.py`.

## File Structure

```
├── main.py                 # FastAPI app with all routes
├── quiz_logic.py           # QuizEngine for question generation & follow-ups
├── fortune_engine.py       # Rule-based fortune generator
├── database.py             # SQLite handler
├── astrology.py            # Astrology utilities
├── requirements.txt        # Python dependencies
├── templates/
│   ├── index.html          # Landing page
│   ├── quiz.html           # Quiz interface
│   └── fortune.html        # Fortune display page
├── static/
│   ├── css/
│   │   └── style.css       # Glass-morphism UI + responsive layout
│   ├── js/
│   │   ├── quiz.js         # Paginated quiz logic with semantic mapping
│   │   └── script.js       # General utilities
│   ├── data/
│   │   └── question.json   # Question bank
│   └── images/
├── tests/
│   └── sanity_test.py      # Endpoint tests (4/4 passing)
└── README.md
```

## Configuration

Key environment variables (set in `main.py` or `.env`):

- `SECRET_KEY`: Admin auth token for `/admin/download_results`
- `FORCE_RULE_BASED`: Set `True` to disable ML and use only rule-based fortunes (default: True)
- `DATABASE_URL`: SQLite DB path (default: `mirror.db`)

## Testing

Run sanity tests:
```bash
python -m pytest tests/sanity_test.py -q
```

Expected: 4 passed

## Building for Mobile (Cordova)

To wrap as iOS/Android app:

1. Install Cordova:
```bash
npm install -g cordova
```

2. Create Cordova project:
```bash
cordova create mirrorapp com.example.mirror MirrorApp
cd mirrorapp
```

3. Copy web assets:
```bash
# Copy templates/index.html and static/ into www/
```

4. Add platforms:
```bash
cordova platform add android
cordova platform add ios  # macOS only
```

5. Build:
```bash
cordova build android
cordova build ios  # macOS only
```

See [Cordova Documentation](https://cordova.apache.org/) for signing and publishing to app stores.

## Known Limitations

- ML model disabled by default (FORCE_RULE_BASED=True) to avoid corrupted output; can be re-enabled with stricter validation
- iOS builds require macOS and Xcode
- Remote API calls require CORS configuration on backend

## Future Enhancements

- Richer follow-up question template library (12+ prompts per trait)
- Admin UI for browsing/filtering quiz results
- Offline support with localStorage caching
- Deep linking and custom URL schemes
- Phased ML re-enablement with validation and staging

## License

MIT (or your choice)

## Contributing

Feel free to open issues and submit pull requests!

## Contact

For questions or feedback, reach out via GitHub issues or email.
