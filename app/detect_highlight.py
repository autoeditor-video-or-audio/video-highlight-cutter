import os
import sys
import logging
import requests
import re
import json
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def read_srt_transcription(srt_path):
    transcription = []
    with open(srt_path, "r", encoding="utf-8") as f:
        for line in f:
            if re.match(r"^\d+$", line.strip()) or "-->" in line:
                continue
            text = line.strip()
            if text:
                transcription.append(text)
    return " ".join(transcription)

def get_audio_duration_from_srt(srt_path):
    end_time = 0.0
    pattern = r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s-->\s(\d{2}):(\d{2}):(\d{2}),(\d{3})"
    with open(srt_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for line in reversed(lines):
        match = re.search(pattern, line)
        if match:
            hours = int(match.group(5))
            minutes = int(match.group(6))
            seconds = int(match.group(7))
            millis = int(match.group(8))
            end_time = hours * 3600 + minutes * 60 + seconds + millis / 1000.0
            break
    return end_time

def load_prompt_from_file(prompt_path):
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

def generate_prompt(prompt_template, transcription_text, audio_duration):
    prompt = prompt_template.replace("TRANSCRIBE", transcription_text)
    prompt = prompt.replace("DURATION", f"{audio_duration:.2f}")
    return prompt

def ensure_ollama_model():
    OLLAMA_HOSTNAME = os.getenv("OLLAMA_HOSTNAME")
    OLLAMA_PORT = os.getenv("OLLAMA_PORT")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
    url_tags = f"http://{OLLAMA_HOSTNAME}:{OLLAMA_PORT}/api/tags"
    url_pull = f"http://{OLLAMA_HOSTNAME}:{OLLAMA_PORT}/api/pull"
    try:
        logger.info(f"Verificando se modelo '{OLLAMA_MODEL}' já está disponível no Ollama...")
        response = requests.get(url_tags, timeout=60)
        response.raise_for_status()
        tags = response.json().get("models", [])
        if any(model["name"] == OLLAMA_MODEL for model in tags):
            logger.info(f"Modelo '{OLLAMA_MODEL}' já está disponível!")
            return True
        logger.info(f"Modelo '{OLLAMA_MODEL}' não encontrado, tentando baixar automaticamente...")
        # Baixa o modelo via /api/pull
        pull_payload = {"name": OLLAMA_MODEL}
        pull_resp = requests.post(url_pull, json=pull_payload, timeout=600)
        pull_resp.raise_for_status()
        logger.info(f"Download do modelo '{OLLAMA_MODEL}' iniciado. Aguardando concluir...")
        # Aguarda até aparecer na lista de tags (até 5 min, checando a cada 5s)
        for _ in range(60):
            response = requests.get(url_tags, timeout=60)
            tags = response.json().get("models", [])
            if any(model["name"] == OLLAMA_MODEL for model in tags):
                logger.info(f"Modelo '{OLLAMA_MODEL}' agora está disponível!")
                return True
            time.sleep(5)
        logger.error(f"Não foi possível baixar o modelo '{OLLAMA_MODEL}' em tempo hábil.")
        return False
    except Exception as e:
        logger.error(f"Erro ao checar/baixar modelo '{OLLAMA_MODEL}': {e}")
        return False

def request_ollama(prompt):
    OLLAMA_HOSTNAME = os.getenv("OLLAMA_HOSTNAME")
    OLLAMA_PORT = os.getenv("OLLAMA_PORT")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
    OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "2400"))

    url = f"http://{OLLAMA_HOSTNAME}:{OLLAMA_PORT}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "prompt": prompt
    }
    logger.info(f"Enviando prompt para {url}...")
    response = requests.post(url, json=payload, timeout=OLLAMA_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    result = data.get("response", "").strip()
    logger.info(f"Resposta do Ollama: {result}")
    return result

def extract_json_list(text):
    """
    Extrai a lista JSON do texto, mesmo que haja comentários antes/depois.
    """
    m = re.search(r'\[.*\]', text, re.DOTALL)
    if m:
        return json.loads(m.group(0))
    # fallback: tenta o texto inteiro
    return json.loads(text)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python detect_highlight.py caminho/do/arquivo.srt caminho/do/prompt.txt")
        sys.exit(1)
    srt_path = sys.argv[1]
    prompt_path = sys.argv[2]
    logger.info(f"Lendo SRT: {srt_path}")

    transcription = read_srt_transcription(srt_path)
    duration = get_audio_duration_from_srt(srt_path)
    logger.info(f"Duração estimada: {duration:.2f} segundos")

    prompt_template = load_prompt_from_file(prompt_path)
    prompt = generate_prompt(prompt_template, transcription, duration)

    if ensure_ollama_model():
        result = request_ollama(prompt)
    else:
        logger.error("O modelo não está disponível e não pôde ser baixado.")
        sys.exit(1)

    highlight_path = os.path.splitext(srt_path)[0] + ".highlight.json"
    try:
        highlight_data = extract_json_list(result)
        # Se veio um dict (um único corte), transforma em lista:
        if isinstance(highlight_data, dict):
            highlight_data = [highlight_data]
        # Salva como lista no JSON, mesmo se só 1 corte
        with open(highlight_path, "w", encoding="utf-8") as f:
            json.dump(highlight_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Highlight(s) salvo(s) em {highlight_path}")
    except Exception as e:
        logger.error(f"Não foi possível processar o resultado do Ollama: {result} - erro: {e}")
