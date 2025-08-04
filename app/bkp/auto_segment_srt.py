import os
import sys
import re
import json

MIN_LEN = float(os.getenv("MIN_LEN", 3))
MAX_LEN = float(os.getenv("MAX_LEN", 30))

def parse_srt(srt_path):
    """
    Lê um arquivo SRT e retorna uma lista de tuplas: (start, end, texto)
    """
    pattern = re.compile(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s-->\s(\d{2}):(\d{2}):(\d{2}),(\d{3})")
    blocks = []
    with open(srt_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    idx, n = 0, len(lines)
    while idx < n:
        # Ignora número da legenda
        while idx < n and not pattern.match(lines[idx]):
            idx += 1
        if idx >= n: break
        # Tempo
        match = pattern.match(lines[idx])
        if not match:
            idx += 1
            continue
        start = int(match.group(1)) * 3600 + int(match.group(2)) * 60 + int(match.group(3)) + int(match.group(4))/1000
        end = int(match.group(5)) * 3600 + int(match.group(6)) * 60 + int(match.group(7)) + int(match.group(8))/1000
        idx += 1
        # Texto
        text_lines = []
        while idx < n and lines[idx].strip() and not pattern.match(lines[idx]):
            text_lines.append(lines[idx].strip())
            idx += 1
        blocks.append((start, end, " ".join(text_lines)))
        # Avança para o próximo bloco
        while idx < n and not lines[idx].strip():
            idx += 1
    return blocks

def group_blocks(blocks, min_len, max_len):
    """
    Agrupa blocos para criar segmentos entre min_len e max_len.
    Nunca ultrapassa max_len e nunca cria corte menor que min_len.
    """
    highlights = []
    i = 0
    while i < len(blocks):
        start = blocks[i][0]
        end = blocks[i][1]
        current_text = [blocks[i][2]]
        j = i + 1
        while j < len(blocks) and (blocks[j][1] - start) <= max_len:
            end = blocks[j][1]
            current_text.append(blocks[j][2])
            if (end - start) >= min_len:
                break
            j += 1
        duration = end - start
        if duration >= min_len and duration <= max_len:
            highlights.append({"start": round(start, 2), "end": round(end, 2)})
        i = j
    return highlights

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python auto_segment_srt.py caminho/do/arquivo.srt")
        sys.exit(1)
    srt_path = sys.argv[1]
    highlight_path = os.path.splitext(srt_path)[0] + ".highlight.json"
    blocks = parse_srt(srt_path)
    highlights = group_blocks(blocks, MIN_LEN, MAX_LEN)
    with open(highlight_path, "w", encoding="utf-8") as f:
        json.dump(highlights, f, ensure_ascii=False, indent=2)
    print(f"{len(highlights)} cortes gerados e salvos em {highlight_path}")
