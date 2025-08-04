import sys
import os
import json
import argparse
import shutil
from moviepy.editor import VideoFileClip

def try_update_status(job_id, message, percent, output_dir):
    if job_id and output_dir:
        try:
            from utils import update_status
            update_status(job_id, message, percent, output_dir)
        except Exception as e:
            print(f"Erro ao atualizar status: {e}")

def read_highlight_times(highlight_path):
    with open(highlight_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

def cut_video_segments(video_path, highlights, job_id=None, output_dir=None):
    base, ext = os.path.splitext(video_path)
    clip_count = 0
    video = VideoFileClip(video_path)
    video_duration = video.duration
    print(f"Duração do vídeo: {video_duration:.2f}s")

    total = len(highlights)
    for idx, seg in enumerate(highlights, 1):
        start = float(seg["start"])
        end = float(seg["end"])
        if start >= video_duration:
            print(f"IGNORADO: Corte {idx} começa em {start:.2f}s (fora do vídeo)")
            continue
        if end > video_duration:
            print(f"AVISO: Corte {idx} fim ajustado de {end:.2f}s para {video_duration:.2f}s (fim do vídeo)")
            end = video_duration
        if start >= end:
            print(f"IGNORADO: Corte {idx} start >= end ({start:.2f}s >= {end:.2f}s)")
            continue
        output_path = f"{base}_highlight{idx}{ext}"
        progress = 80 + int((idx-1)/total * 15)  # 80 a 95%
        try_update_status(job_id, f"Cortando vídeo ({idx}/{total})...", progress, output_dir)
        print(f"Cortando de {start:.2f}s a {end:.2f}s -> {output_path}")
        subclip = video.subclip(start, end)
        subclip.write_videofile(output_path, codec="libx264")
        print(f"Vídeo salvo em {output_path}")
        clip_count += 1

        # NOVO BLOCO: move highlight já para processed/output_dir se fornecido
        if output_dir:
            dest = os.path.join(output_dir, os.path.basename(output_path))
            if os.path.abspath(output_path) != os.path.abspath(dest):
                try:
                    shutil.move(output_path, dest)
                    print(f"Highlight movido: {output_path} -> {dest}")
                except Exception as e:
                    print(f"Erro ao mover highlight {output_path}: {e}")

    print(f"{clip_count} clipes gerados com sucesso.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Corta os highlights de um vídeo.")
    parser.add_argument("video_path", help="Caminho do vídeo original")
    parser.add_argument("highlight_path", help="Arquivo .json com os highlights")
    parser.add_argument("--job_id", default=None, help="Identificador do job (opcional)")
    parser.add_argument("--output_dir", default=None, help="Diretório dos status (opcional)")

    args = parser.parse_args()
    highlights = read_highlight_times(args.highlight_path)
    cut_video_segments(args.video_path, highlights, args.job_id, args.output_dir)
