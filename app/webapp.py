from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Request, APIRouter
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import shutil
import os
import uuid
import subprocess
import json

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

@app.post("/upload")
async def upload_video(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    ext = Path(file.filename).suffix
    uid = uuid.uuid4().hex
    save_path = UPLOAD_DIR / f"{uid}{ext}"
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Limpa apenas arquivos de highlight ao receber NOVO UPLOAD
    for f in PROCESSED_DIR.glob("*_highlight*.mp4"):
        try: f.unlink()
        except: pass

    background_tasks.add_task(process_video, save_path, uid)
    return {"message": "Arquivo recebido! Processando...", "id": uid}


def process_video(video_path, job_id):
    # Garante que o main.py recebe o job_id e output_dir correto
    subprocess.call([
        "python", "main.py", str(video_path),
        "--output_dir", str(PROCESSED_DIR),
        "--job_id", str(job_id)
    ])

@app.get("/download/{filename}")
def download_highlight(filename: str):
    file_path = PROCESSED_DIR / filename
    if not file_path.exists():
        return JSONResponse(content={"error": "Arquivo não encontrado!"}, status_code=404)
    return FileResponse(str(file_path), media_type="video/mp4", filename=filename)

@app.get("/status/{job_id}")
def job_status(job_id: str):
    status_path = PROCESSED_DIR / f"status_{job_id}.json"
    # Garante highlights prontos
    highlights = sorted(PROCESSED_DIR.glob("*_highlight*.mp4"))
    highlight_names = [f.name for f in highlights]
    if not status_path.exists():
        return {"step": "Aguardando processamento...", "progress": 0, "highlights": highlight_names}
    with open(status_path, encoding="utf-8") as f:
        data = json.load(f)
    # Sempre inclui os highlights atuais
    data["highlights"] = highlight_names
    return data


app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
