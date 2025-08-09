from pathlib import Path
from typing import List

# Base: app/prompts/detect_highlight
DETECT_BASE = Path(__file__).resolve().parent / "detect_highlight"

def list_detect_prompts() -> List[str]:
    if not DETECT_BASE.exists():
        return []
    return sorted(p.stem for p in DETECT_BASE.glob("*.txt"))

def read_detect_prompt(name: str) -> str:
    safe = "".join(ch for ch in name if ch.isalnum() or ch in ("-", "_"))
    path = DETECT_BASE / f"{safe}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt '{safe}' não encontrado em detect_highlight.")
    return path.read_text(encoding="utf-8")

def resolve_by_name_or_default(name: str | None) -> Path:
    """Retorna o caminho do prompt por nome ou default.txt (se existir)."""
    if name:
        p = DETECT_BASE / f"{name}.txt"
        if p.exists():
            return p
        raise FileNotFoundError(f"Prompt '{name}.txt' não encontrado em {DETECT_BASE}")
    # default
    p_default = DETECT_BASE / "default.txt"
    if p_default.exists():
        return p_default
    # fallback legado (se existir)
    legacy = Path(__file__).resolve().parent.parent / "prompts" / "prompt_detect_highlight.txt"
    return legacy  # pode não existir — o chamador decide o que fazer
