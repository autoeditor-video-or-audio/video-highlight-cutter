import os
import sys
import logging
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def save_as_srt(segments, srt_path):
    def format_timestamp(seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

    with open(srt_path, "w", encoding="utf-8") as f:
        for idx, seg in enumerate(segments, 1):
            start = format_timestamp(seg.get("start", 0))
            end = format_timestamp(seg.get("end", 0))
            text = seg.get("text", "").strip()
            f.write(f"{idx}\n{start} --> {end}\n{text}\n\n")
    logger.info(f"Legenda SRT salva em {srt_path}")

def transcribe_audio_whisper(file_path):
    # Lê configs do ENV
    API_TRANSCRIBE_URL = os.getenv("API_TRANSCRIBE_URL", "localhost")
    API_TRANSCRIBE_PORT = os.getenv("API_TRANSCRIBE_PORT", "9000")
    API_TRANSCRIBE_TIMEOUT = int(os.getenv("API_TRANSCRIBE_TIMEOUT", "2400"))  # 40 minutos

    logger.info(f"Timeout configurado para transcrição: {API_TRANSCRIBE_TIMEOUT} segundos")
    api_url = f"http://{API_TRANSCRIBE_URL}:{API_TRANSCRIBE_PORT}/asr"
    logger.info(f"Enviando {file_path} para {api_url}...")

    try:
        headers = {'accept': 'application/json'}
        params = {
            'task': 'transcribe',
            'language': 'pt',
            'encode': 'true',
            'output': 'json',
            'word_timestamps': 'true',
        }
        with open(file_path, 'rb') as audio_file:
            files = {'audio_file': audio_file}
            response = requests.post(api_url, params=params, headers=headers, files=files, timeout=API_TRANSCRIBE_TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            if "segments" in data and isinstance(data["segments"], list) and len(data["segments"]) > 0:
                # Salva como SRT segmentado (com tempo!)
                srt_path = os.path.splitext(file_path)[0] + ".srt"
                save_as_srt(data["segments"], srt_path)
                return srt_path
            else:
                # Fallback: só texto bruto, sem tempo
                transcription = data.get("text", response.text)
                sst_path = os.path.splitext(file_path)[0] + ".sst"
                with open(sst_path, "w", encoding="utf-8") as f:
                    f.write(transcription)
                logger.info(f"Transcrição salva em {sst_path}")
                return sst_path
        else:
            logger.error(f"Erro na transcrição: Status {response.status_code}. Resposta: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Erro durante a transcrição: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python transcribe_audio_whisper.py caminho/do/audio.mp3")
        sys.exit(1)
    mp3_path = sys.argv[1]
    transcribe_audio_whisper(mp3_path)
