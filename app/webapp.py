from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Request, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import shutil
import os
import uuid
import subprocess
import json
from datetime import datetime

# prompts loader
from prompts.loader import list_detect_prompts, read_detect_prompt, resolve_by_name_or_default

app = FastAPI()
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
PROCESSED_DIR = BASE_DIR / "processed"
TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / "templates"))

UPLOAD_DIR.mkdir(exist_ok=True)
PROCESSED_DIR.mkdir(exist_ok=True)

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    highlights = sorted(PROCESSED_DIR.glob("*_highlight*.mp4"))
    return TEMPLATES.TemplateResponse("index.html", {"request": request, "highlights": highlights})

# ---------- API de prompts detect_highlight ----------
@app.get("/api/prompts/detect_highlight")
def api_list_detect_prompts():
    items = [{"name": n, "label": n.replace("_", " ")} for n in list_detect_prompts()]
    return {"items": items}

@app.get("/api/prompts/detect_highlight/{name}")
def api_get_detect_prompt(name: str):
    try:
        content = read_detect_prompt(name)
        return {"name": name, "content": content}
    except FileNotFoundError as e:
        return JSONResponse({"error": str(e)}, status_code=404)

# ---------- Upload recebe prompt_name OU prompt_text ----------
@app.post("/upload")
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    prompt_name: str | None = Form(default=None),
    prompt_text: str | None = Form(default=None),
):
    ext = Path(file.filename).suffix
    uid = uuid.uuid4().hex
    save_path = UPLOAD_DIR / f"{uid}{ext}"
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # limpa apenas highlights antigos quando novo upload chega
    for f in PROCESSED_DIR.glob("*_highlight*.mp4"):
        try:
            f.unlink()
        except:
            pass

    # Resolver prompt_path
    prompt_path = None
    if prompt_text and prompt_text.strip():
        tmp_prompt = UPLOAD_DIR / f"{uid}_prompt.txt"
        tmp_prompt.write_text(prompt_text, encoding="utf-8")
        prompt_path = str(tmp_prompt)
    else:
        p = resolve_by_name_or_default(prompt_name)
        if p.exists():
            prompt_path = str(p.resolve())
        else:
            prompt_path = ""

    background_tasks.add_task(process_video, save_path, uid, prompt_path)
    return {"message": "Arquivo recebido! Processando...", "id": uid}

def process_video(video_path: Path, job_id: str, prompt_path: str):
    """
    Chama o pipeline passando --prompt_path para o main.py.
    """
    cmd = [
        "python", "main.py", str(video_path),
        "--output_dir", str(PROCESSED_DIR),
        "--job_id", str(job_id)
    ]
    if prompt_path:
        cmd += ["--prompt_path", prompt_path]

    subprocess.call(cmd)

@app.get("/download/{filename}")
def download_highlight(filename: str):
    file_path = PROCESSED_DIR / filename
    if not file_path.exists():
        return JSONResponse(content={"error": "Arquivo não encontrado!"}, status_code=404)
    return FileResponse(str(file_path), media_type="video/mp4", filename=filename)

@app.get("/status/{job_id}")
def job_status(job_id: str):
    status_path = PROCESSED_DIR / f"status_{job_id}.json"
    highlights = sorted(PROCESSED_DIR.glob("*_highlight*.mp4"))
    highlight_names = [f.name for f in highlights]

    if not status_path.exists():
        return {
            "step": "Aguardando processamento...",
            "progress": 0,
            "highlights": highlight_names
        }

    with open(status_path, encoding="utf-8") as f:
        data = json.load(f)
    data["highlights"] = highlight_names
    return data

# monta pasta static
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
