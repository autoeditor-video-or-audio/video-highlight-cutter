import os
import sys
import json
import requests
import re

def parse_srt(srt_path):
    pattern = re.compile(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s-->\s(\d{2}):(\d{2}):(\d{2}),(\d{3})")
    blocks = []
    with open(srt_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    idx, n = 0, len(lines)
    while idx < n:
        while idx < n and not pattern.match(lines[idx]):
            idx += 1
        if idx >= n: break
        match = pattern.match(lines[idx])
        if not match:
            idx += 1
            continue
        start = int(match.group(1)) * 3600 + int(match.group(2)) * 60 + int(match.group(3)) + int(match.group(4))/1000
        end = int(match.group(5)) * 3600 + int(match.group(6)) * 60 + int(match.group(7)) + int(match.group(8))/1000
        idx += 1
        text_lines = []
        while idx < n and lines[idx].strip() and not pattern.match(lines[idx]):
            text_lines.append(lines[idx].strip())
            idx += 1
        blocks.append((start, end, " ".join(text_lines)))
        while idx < n and not lines[idx].strip():
            idx += 1
    return blocks

def get_text_for_segment(blocks, seg_start, seg_end):
    text = []
    for start, end, content in blocks:
        if end > seg_start and start < seg_end:
            text.append(content)
    return " ".join(text)

def load_prompt_from_file(prompt_path):
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

def request_ollama(text, prompt_template):
    OLLAMA_HOSTNAME = os.getenv("OLLAMA_HOSTNAME")
    OLLAMA_PORT = os.getenv("OLLAMA_PORT")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
    OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))

    url = f"http://{OLLAMA_HOSTNAME}:{OLLAMA_PORT}/api/generate"
    prompt = prompt_template.replace("TRECHO_AQUI", text)
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "prompt": prompt
    }
    response = requests.post(url, json=payload, timeout=OLLAMA_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    result = data.get("response", "").strip()
    return result

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Uso: python classify_segments.py caminho/do/arquivo.srt caminho/do/highlight.json caminho/do/prompt_classify.txt")
        sys.exit(1)
    srt_path = sys.argv[1]
    highlight_path = sys.argv[2]
    prompt_path = sys.argv[3]

    prompt_template = load_prompt_from_file(prompt_path)

    blocks = parse_srt(srt_path)
    with open(highlight_path, "r", encoding="utf-8") as f:
        highlights = json.load(f)

    result_highlights = []
    ignored = 0
    for seg in highlights:
        seg_start = float(seg["start"])
        seg_end = float(seg["end"])
        seg_text = get_text_for_segment(blocks, seg_start, seg_end)
        if not seg_text.strip():
            print(f"Ignorado corte {seg_start}-{seg_end}s (sem texto encontrado no SRT)")
            ignored += 1
            continue
        score = request_ollama(seg_text, prompt_template)
        try:
            score_num = int(re.findall(r'\d+', score)[0])
        except Exception:
            score_num = 0
        result_highlights.append({
            "start": seg_start,
            "end": seg_end,
            "score": score_num,
            "text": seg_text
        })
        print(f"Corte {seg_start}-{seg_end}s: nota {score_num}")

    output_json = os.path.splitext(highlight_path)[0] + ".classified.json"
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(result_highlights, f, ensure_ascii=False, indent=2)
    print(f"\nCortes classificados salvos em {output_json}")
    print(f"{ignored} cortes ignorados por não terem texto correspondente.")
