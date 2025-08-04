import json
from pathlib import Path

def update_status(job_id, step, progress, output_dir="processed"):
    """Salva o status do processamento no arquivo status_{job_id}.json"""
    status_path = Path(output_dir) / f"status_{job_id}.json"
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump({"step": step, "progress": progress}, f)
