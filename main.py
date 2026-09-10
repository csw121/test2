from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import Optional
import sqlite3
import uuid

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "app.db"
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Photo Memo Board")
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            image_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


init_db()


@app.get("/")
async def index():
    return templates.TemplateResponse("index.html", {"request": {}})


@app.get("/api/memos")
async def get_memos():
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT id, content, image_path, created_at FROM memos ORDER BY id DESC"
    ).fetchall()
    conn.close()

    memos = [
        {
            "id": row["id"],
            "content": row["content"],
            "image_path": row["image_path"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]
    return JSONResponse(content={"memos": memos})


@app.post("/api/memos")
async def create_memo(
    content: str = Form(...),
    image: Optional[UploadFile] = File(None),
):
    if not content or not content.strip():
        raise HTTPException(status_code=400, detail="메모 내용을 입력해주세요.")

    image_path = None
    if image is not None and image.filename:
        filename = f"{uuid.uuid4().hex}_{image.filename}"
        save_path = UPLOAD_DIR / filename
        with save_path.open("wb") as f:
            content_bytes = await image.read()
            f.write(content_bytes)
        image_path = f"/uploads/{filename}"

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO memos (content, image_path) VALUES (?, ?)",
        (content, image_path),
    )
    conn.commit()
    memo_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    conn.close()

    return JSONResponse(
        status_code=201,
        content={
            "message": "메모가 저장되었습니다.",
            "id": memo_id,
            "image_path": image_path,
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
