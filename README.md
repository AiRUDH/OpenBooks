# OpenBooks

Minimal PDF library — upload, store, and read PDFs in the browser.

**Stack:** FastAPI · SQLite · JWT · Vanilla JS

---

## Setup

```powershell
# 1. create & activate venv with uv
uv venv
.venv\Scripts\activate

# 2. install deps
uv pip install -e .

# 3. run
uv run python run.py
```

Open **http://localhost:8000** — register, login, upload PDFs, read them.

---

## Project layout

```
openbooks/
├── backend/
│   └── main.py          # FastAPI app (auth + books API)
├── frontend/
│   └── index.html       # SPA (no framework)
├── uploads/             # stored PDFs (auto-created)
├── openbooks.db         # SQLite (auto-created)
├── pyproject.toml       # uv/pip deps
└── run.py               # uvicorn launcher
```

## API

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/register` | — | Create account |
| POST | `/api/login` | — | Get JWT token |
| GET | `/api/me` | ✓ | Whoami |
| GET | `/api/books` | ✓ | List all books |
| POST | `/api/books` | ✓ | Upload PDF |
| DELETE | `/api/books/{id}` | ✓ | Delete own book |

## Env vars

| Var | Default | Description |
|-----|---------|-------------|
| `SECRET_KEY` | `change-me-…` | JWT signing key (change in prod!) |
