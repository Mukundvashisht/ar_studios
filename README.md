<!-- ## CRM/Project Management App (Flask) -->
## AR Studios Website/Project Management App (Flask)

Modern Flask-based CRM and lightweight project management app with authentication, role-based access, admin CMS, project tracking, file uploads, and a real-time project chat powered by Socket.IO.

### Highlights
- **Flask 3 + SQLAlchemy 2** with `Flask-Login`
- **PostgreSQL** by default; auto table creation on first run
- **Socket.IO** chat on project pages
- **Blueprints**: `auth`, `profile`, `projects`, `admin`, `api`
- **Responsive templates** with Jinja2 and static assets
- **File uploads** for projects and featured works

---

## Tech Stack
- Backend: `Flask`, `Flask-SQLAlchemy`, `Flask-Login`, `Flask-SocketIO`
- DB: PostgreSQL (driver: `psycopg2-binary`)
- Templating: Jinja2
- Realtime: Socket.IO (`python-socketio`)
- Config: `python-dotenv`

## Repository Structure
```
app.py              # App initialization, DB setup, blueprint registration, Socket.IO entrypoint
models.py           # SQLAlchemy models (User, Project, Assignments, ChatMessage, etc.)
routes.py           # Public pages (home, about, dashboard), helpers
auth_routes.py      # Login, registration, forgot password
profile_routes.py   # Profile and settings
project_routes.py   # Projects CRUD, detail, chat, milestones, assignment
admin_routes.py     # Admin CMS (users, clients, featured works) + uploads
api_routes.py       # Auth-protected JSON API (e.g., /api/projects)
templates/          # Jinja templates (auth/, admin/, projects/, profile/, etc.)
static/             # CSS, JS, uploads/
requirements.txt    # Python dependencies
```

---

## Prerequisites
- Python 3.11+
- PostgreSQL 13+ (or a managed service)
- Node is NOT required (vanilla JS only)

Optional (local DB): Docker Desktop

---

## Quick Start (Local)
1) Clone and enter the project directory
```powershell
git clone <your-repo-url>.git
cd "try3 - Copy"
```

2) Create a virtual environment and install dependencies
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

3) Configure environment variables (.env)
Create a `.env` file in the project root:
```ini
SESSION_SECRET=change-this-in-production

# PostgreSQL connection parts
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=crm_db

# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

4) Ensure PostgreSQL database exists
- Create the database `crm_db` (or the name you chose).
- The app will run `db.create_all()` automatically on startup.

5) Run the app (development)
```powershell
python app.py
```
Visit `http://localhost:5000`.

On first run, the app will create tables. If there are no users, it may initialize sample data depending on conditions in `app.py`.

---

## Environment Configuration
`app.py` builds the SQLAlchemy URI from parts:
```
postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}
```

Notes:
- `SESSION_SECRET` secures Flask session cookies.
- Reverse proxy friendliness via `ProxyFix` is enabled.
- SQLite support is possible by switching the commented URI in `app.py` if desired.

---

## Database
- ORM: SQLAlchemy 2 with declarative base
- Auto-creation: `db.create_all()` on startup
- No Alembic migrations configured by default

If you alter models in `models.py`, you may need to reset the DB in development. `app.py` contains a `reset_database()` helper and logic that can reset when schema mismatches are detected.

---

## Running With Reload and Debug
`python app.py` already starts the Socket.IO server in debug mode.

If you prefer `flask run`, set `FLASK_APP=app.py` and ensure Socket.IO is correctly initialized in that mode. The repository defaults to the explicit `python app.py` entrypoint.

---

## API Overview
All API routes are registered under the `api` blueprint and generally require authentication.

- POST `/api/projects` — Create a project
  - Body: JSON with `name`, `description`, `department`, `priority` (required), `status`, `progress`
  - Returns: created project JSON and logs an `Activity`
- GET `/api/projects` — List all projects (JSON)

More endpoints may exist; inspect `api_routes.py` for details and extend accordingly.

---

## Web Routes (Selected)
- Public pages from `routes.py`: `home`, `service`, `about`, `dashboard` (requires auth)
- Auth (`/auth/*`): login, register, forgot password
- Profile (`/profile/*`): profile, settings, notifications, change password
- Projects (root namespace): list, create, detail, edit, milestones, chat, assign
- Admin (`/admin/*`): users, clients, featured works management

Templates live under `templates/` and static assets are under `static/`.

---

## Realtime Chat
- `Flask-SocketIO` is initialized in `app.py` with CORS `*`
- Project chat is integrated into project detail templates and `project_routes.py`

---

## File Uploads
- Upload logic in `admin_routes.py` (helpers like `ensure_upload_dir`, `save_upload`)
- Files are stored under `static/uploads/` (e.g., `projects/<id>/`, `featured_works/`)
- Ensure your deployment allows persistent storage or use an external object store (S3, etc.)

---

## Deployment

### Gunicorn (Linux)
`gunicorn` is included for production WSGI. For Socket.IO, use the eventlet or gevent worker:
```bash
pip install eventlet
gunicorn -k eventlet -w 1 app:app --bind 0.0.0.0:5000
```

Alternatively, run the Socket.IO server directly via `python app.py` behind a reverse proxy (Nginx) and process manager (systemd, Supervisor).

### Environment
- Set the same `.env` variables in your platform (Render, Railway, Fly.io, etc.)
- Ensure Postgres connectivity from your app to the DB instance

### Static and Uploads
- Serve `/static` via the app or your proxy
- Persist or externalize `static/uploads/` in production

---

## Development Tips
- Keep `requirements.txt` pinned; update regularly
- Add Alembic for migrations if your schema evolves
- Consider implementing CSRF protection if adding forms that mutate state

---

## Troubleshooting
- "column user.role does not exist": the app can reset DB in dev when it detects schema drift; see `app.py`
- Database connection errors: verify all `DB_*` vars and network access
- File uploads failing: check `static/uploads/` permissions and existence

---

## Scripts and Commands (Windows PowerShell)
```powershell
# Create venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install
pip install -r requirements.txt

# Run (dev)
python app.py
```

---
<!-- 
## Contributing
PRs and issues are welcome. Please open an issue describing the change before large contributions.

## License
MIT (or your preferred license) -->

