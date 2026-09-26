# KAA — Korea Assist App

> Status: This project is still under development and is not finished. It is a local development build and not production-ready.

Local development release, not production-ready. This ZIP contains all existing source files, sample content, tests and configuration examples. It does not claim full completion of the original product specification.

## Run locally

Install Python 3.11 or newer (with SQLite support). No third-party Python packages are required.

1. Extract the ZIP.
2. Open the `kaa-korea-assist` folder in VS Code or a terminal.
3. Run:

```sh
python server.py
```

On macOS/Linux, use `python3 server.py` if necessary. On Windows, `py server.py` also works.

4. Open **http://localhost:3000** in a browser. Do not open index.html directly.
5. Choose **Explore demo**, or create an account using a password of at least 10 characters.

The desktop layout includes a 393 × 852 phone preview. Browser developer tools can also simulate an iPhone 15 Pro viewport. This is a browser application, not a signed native iOS/Android app.

## Storage

The SQLite database is created automatically at `backend/database/kaa.sqlite3`. Accounts, profiles and learning state persist across server restarts. Do not commit or share that database. The included ZIP excludes runtime databases and secrets. Demo creates an isolated sample account on each use.

## Optional AI and search setup

Copy `.env.example` to `.env` in the project root. Set:

- `AI_API_KEY`: your chat-completions API key
- `AI_BASE_URL`: compatible HTTPS API base URL, without `/chat/completions`
- `AI_MODEL`: a model supported by your account
- `SEARCH_API_KEY`: optional Brave Search API key

Restart the server after editing environment variables. Enable AI consent in Profile before sending a chat question. API keys stay on the server. Without a key, chat returns a clearly labelled setup guide, not a simulated AI response. Live paid API calls have not been tested.

Official-source search filters results to allowlisted domains. It retrieves search excerpts, not independently verified full pages. This is not a complete RAG ingestion/indexing pipeline.

## Editing the project

- Colors and visual design: `public/styles.css`, particularly `:root` variables.
- UI, forms and routing: `public/app.js`.
- University directory: `src/data/universities.json`. Include an ID, name, homepage, internationalOffice, domains and topics, following existing examples. Procedures currently point to office starting pages, not verified procedure pages.
- Lessons and quizzes: `src/data/lessons.json`. Follow an existing lesson object. Supported exercise renderers include selection, text input, listening and ordering; matching is presently a simple selection exercise.
- Visa overviews: `src/data/visas.json`. Have qualified editors verify official current evidence before adding requirements or verification dates.
- Document planning: `src/data/processes.json`. Lists are illustrative, not official requirements.
- Updates: `src/data/updates.json`. Entries are locally curated; no live feed ingester is included.
- Websites: users add/edit/remove/reorder/favorite their own links on My Websites.
- AI instructions: `backend/services/system-prompt.txt`.
- Languages: `src/locales/*.json` are editable catalogs; copy changed catalogs to matching `public/locales/*.json` files, which the browser actually loads. New language codes also require updates to the language map and RTL list in `public/app.js`, validation in `server.py`, and the public cache list in `public/sw.js`.

Restart the server and reload the browser after content changes. A service worker caches public learning content; remove site data/service workers in browser developer tools if a stale cache persists.

## Architecture

- `server.py`: standard-library HTTP development server, session/auth APIs, SQLite persistence, AI and search integration.
- `backend/database/schema.sql`: users, sessions and per-user JSON state.
- `backend/services/system-prompt.txt`: editable AI guidance.
- `src/data/`: JSON-backed editorial content (universities, lessons, visas, updates and process checklists).
- `src/locales/` and `public/locales/`: source and served translation catalogs.
- `public/`: HTML/CSS/JavaScript app, service worker, manifest and SVG logo.
- `tests/test_app.py`: backend integration tests.

Universities and lessons are JSON-backed, not relational database tables. There is no admin dashboard. The frontend is vanilla JavaScript; this is not a React/Next.js/TypeScript project. The Python development server makes setup simple but must not be treated as a production hosting stack.

## Tests

```sh
python -m unittest discover -s tests -v
```

With Node.js installed, optional JavaScript syntax check:

```sh
node --check public/app.js
```

Packaging verification: 8 backend tests passed; JavaScript syntax check passed. The Python test run emitted unclosed SQLite connection ResourceWarnings, a known cleanup issue. Full browser/device/accessibility tests have not been completed.

## Important limitations

- This is a partial functional development build, not completion of all 52 requested sections.
- Ten language catalogs and RTL switching exist, but most extended text falls back to English; editorial content and some UI text remain English/Korean.
- Curriculum is 12 introductory lessons, not a complete adaptive Korean course. Device speech depends on installed voices.
- Immigration guidance, university policies and emergency directory entries require current official verification before production.
- Reminders run while opening the app. No scheduled background or push notifications.
- Saved websites open manually; no automatic website change detection.
- Updates are sample/editorial resources, not current aggregated news or live job listings.
- Offline cache covers public assets/content; authenticated offline profile editing and progress synchronization are not implemented.
- No email verification, password reset, production deployment, admin editor, voice evaluation, camera translation, document scanning or community system.
- Per-user state is saved as one JSON object; concurrent tabs can overwrite each other's changes.

## Security and privacy

Passwords use salted scrypt hashes. Sessions use HttpOnly and SameSite cookies; HTTPS configuration enables Secure cookies. Request origin checks, body limits, basic input validation, CSP and process-local rate limits are included. Profile details and tokens must be treated as sensitive. No third-party frontend trackers are included.

Before public deployment: use a production server behind HTTPS; disable demo (`DEMO_ENABLED=false`); configure the exact APP_ORIGIN; improve validation, database connection lifecycle and abuse prevention; add account recovery and monitoring; review provider privacy retention; audit security/accessibility; verify official content; and arrange backups. Rate limits are in-memory and reset on restart.
