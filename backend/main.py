from fastapi import (
    FastAPI, Depends, HTTPException, status,
    UploadFile, File, Form
)
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Annotated
from pathlib import Path
import aiosqlite
import shutil
import uuid
import os

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

# ─── Config ────────────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production-use-a-long-random-string")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day

DB_PATH = Path("openbooks.db")
UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(exist_ok=True)

# ─── Schemas ───────────────────────────────────────────────────────────────────
class Token(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    username: str
    password: str

class BookOut(BaseModel):
    id: int
    title: str
    filename: str      # original filename (display only)
    filepath: str      # actual stored filename (uuid_original)
    uploaded_by: str
    created_at: str

# ─── Auth helpers ──────────────────────────────────────────────────────────────
# ─── Auth helpers ──────────────────────────────────────────────────────────────
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

def hash_password(password: str) -> str:
    """Hash password safely - bcrypt only supports up to 72 bytes"""
    if len(password.encode('utf-8')) > 72:
        password = password[:72]
    return pwd_ctx.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)

def create_access_token(sub: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": sub, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

# ─── DB helpers ────────────────────────────────────────────────────────────────
async def get_db():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                filename    TEXT NOT NULL,
                filepath    TEXT NOT NULL,
                uploaded_by TEXT NOT NULL,
                created_at  TEXT NOT NULL
            )
        """)
        await db.commit()

# ─── Current user dependency ───────────────────────────────────────────────────
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: aiosqlite.Connection = Depends(get_db),
) -> str:
    creds_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise creds_exc
    except JWTError:
        raise creds_exc

    async with db.execute("SELECT username FROM users WHERE username = ?", (username,)) as cur:
        row = await cur.fetchone()
    if row is None:
        raise creds_exc
    return username

# ─── App ───────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="OpenBooks", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded PDFs
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

# Serve frontend (must be last)
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

# ─── Auth routes ───────────────────────────────────────────────────────────────
@app.post("/api/register", status_code=201)
async def register(user: UserCreate, db: aiosqlite.Connection = Depends(get_db)):
    async with db.execute("SELECT id FROM users WHERE username = ?", (user.username,)) as cur:
        if await cur.fetchone():
            raise HTTPException(status_code=400, detail="Username already taken")
    await db.execute(
        "INSERT INTO users (username, password) VALUES (?, ?)",
        (user.username, hash_password(user.password)),
    )
    await db.commit()
    return {"message": "Registered successfully"}

@app.post("/api/login", response_model=Token)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: aiosqlite.Connection = Depends(get_db),
):
    async with db.execute(
        "SELECT password FROM users WHERE username = ?", (form.username,)
    ) as cur:
        row = await cur.fetchone()
    if not row or not verify_password(form.password, row["password"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    return {"access_token": create_access_token(form.username), "token_type": "bearer"}

@app.get("/api/me")
async def me(username: str = Depends(get_current_user)):
    return {"username": username}

# ─── Books routes ──────────────────────────────────────────────────────────────
@app.get("/api/books", response_model=list[BookOut])
async def list_books(
    db: aiosqlite.Connection = Depends(get_db),
    _: str = Depends(get_current_user),
):
    async with db.execute(
        "SELECT id, title, filename, filepath, uploaded_by, created_at FROM books ORDER BY id DESC"
    ) as cur:
        rows = await cur.fetchall()
    return [dict(r) for r in rows]

@app.post("/api/books", response_model=BookOut, status_code=201)
async def upload_book(
    title: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    username: str = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    # Unique filename to avoid collisions
    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    dest = UPLOADS_DIR / safe_name

    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    now = datetime.now(timezone.utc).isoformat()
    async with db.execute(
        "INSERT INTO books (title, filename, filepath, uploaded_by, created_at) VALUES (?,?,?,?,?)",
        (title, file.filename, safe_name, username, now),
    ) as cur:
        book_id = cur.lastrowid
    await db.commit()

    return BookOut(
        id=book_id, title=title, filename=file.filename,
        filepath=safe_name, uploaded_by=username, created_at=now,
    )

@app.delete("/api/books/{book_id}", status_code=204)
async def delete_book(
    book_id: int,
    username: str = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    async with db.execute("SELECT filepath, uploaded_by FROM books WHERE id = ?", (book_id,)) as cur:
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Book not found")
    if row["uploaded_by"] != username:
        raise HTTPException(status_code=403, detail="You can only delete your own books")

    (UPLOADS_DIR / row["filepath"]).unlink(missing_ok=True)
    await db.execute("DELETE FROM books WHERE id = ?", (book_id,))
    await db.commit()

# ─── Frontend fallback ─────────────────────────────────────────────────────────
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
