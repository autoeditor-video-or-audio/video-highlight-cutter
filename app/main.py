import argparse
import os
import subprocess
from moviepy.editor import VideoFileClip
from utils import update_status
import glob
import shutil
from pathlib import Path

def extrair_audio(video_path, audio_path=None):
    if not audio_path:
        audio_path = os.path.splitext(video_path)[0] + ".mp3"
    video = VideoFileClip(video_path)
    video.audio.write_audiofile(audio_path)
    print(f"Áudio extraído para: {audio_path}")
    return audio_path

def safe_delete(filepath):
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            print(f"Arquivo deletado: {filepath}")
        except Exception as e:
            print(f"Erro ao deletar {filepath}: {e}")

def main(video_file, output_dir, job_id):
    # 1. Extrai áudio
    update_status(job_id, "Extraindo áudio...", 5, output_dir)
    mp3_file = extrair_audio(video_file)
    
    # 2. Transcreve áudio
    update_status(job_id, "Transcrevendo áudio...", 20, output_dir)
    subprocess.run(["python", "transcreve_whisper.py", mp3_file])

    # 3. Detecta highlights
    srt_file = os.path.splitext(mp3_file)[0] + ".srt"
    if os.path.exists(srt_file):
        update_status(job_id, "Detectando highlights...", 40, output_dir)
        subprocess.run(["python", "detect_highlight.py", srt_file, "prompt_detect_highlight.txt"])
    else:
        update_status(job_id, f"Arquivo {srt_file} não encontrado! Falhou.", 100, output_dir)
        return

    # 4. Corta vídeo
    highlight_json = os.path.splitext(mp3_file)[0] + ".highlight.json"
    if os.path.exists(highlight_json):
        update_status(job_id, "Cortando vídeo...", 80, output_dir)
        subprocess.run([
            "python", "cut_highlight.py", video_file, highlight_json,
            "--job_id", job_id, "--output_dir", output_dir
        ])
    else:
        update_status(job_id, f"Arquivo {highlight_json} não encontrado! Falhou.", 100, output_dir)
        return

    # 5. Limpa arquivos intermediários na pasta uploads e outros do job
    update_status(job_id, "Finalizando e limpando arquivos...", 95, output_dir)

    # Determina o prefixo para apagar arquivos do job
    job_prefix = Path(video_file).stem  # Ex: 377b5641b9fd4c449072a29cfe
    uploads_dir = Path(video_file).parent

    # Remove todos os arquivos relacionados ao job_id na pasta uploads
    for f in uploads_dir.glob(f"{job_prefix}*"):
        safe_delete(str(f))

    # Também remove arquivos intermediários do output_dir, se existirem
    files_to_delete = [
        mp3_file, srt_file, highlight_json, video_file
    ]
    base_name = os.path.splitext(mp3_file)[0]
    for ext in [".classified.json", ".filtered.json"]:
        extra_file = base_name + ext
        if os.path.exists(extra_file):
            files_to_delete.append(extra_file)
    for file in files_to_delete:
        safe_delete(file)

    update_status(job_id, "Concluído!", 100, output_dir)
    print("Processamento concluído!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extrai highlights de um vídeo e corta trechos.")
    parser.add_argument("video_file", help="Caminho do arquivo de vídeo .mp4")
    parser.add_argument("--output_dir", default="processed", help="Diretório para arquivos gerados")
    parser.add_argument("--job_id", required=True, help="Identificador do job para controle de status")
    args = parser.parse_args()
    main(args.video_file, args.output_dir, args.job_id)
