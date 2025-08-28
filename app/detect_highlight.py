import os
import sys
import logging
import requests
import re
import json
import time
import argparse
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --------------------------
# Utilidades
# --------------------------
def env_flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "y", "on")

# --------------------------
# Utilidades de transcrição
# --------------------------
def read_srt_transcription(srt_path: str) -> str:
    transcription = []
    with open(srt_path, "r", encoding="utf-8") as f:
        for line in f:
            if re.match(r"^\d+$", line.strip()) or "-->" in line:
                continue
            text = line.strip()
            if text:
                transcription.append(text)
    return " ".join(transcription)

def get_audio_duration_from_srt(srt_path: str) -> float:
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

# --------------------------
# Prompt helpers
# --------------------------
def load_prompt_from_file(prompt_path: str) -> str:
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

def resolve_prompt_text(prompt_path: Optional[str], prompt_inline: Optional[str]) -> str:
    """
    Prioridade:
      1) prompt_inline (CLI)
      2) PROMPT_TEXT (ENV)
      3) prompt_path (arquivo .txt)
    """
    if prompt_inline and prompt_inline.strip():
        return prompt_inline

    env_prompt = os.getenv("PROMPT_TEXT")
    if env_prompt and env_prompt.strip():
        return env_prompt

    if prompt_path:
        return load_prompt_from_file(prompt_path)

    raise FileNotFoundError(
        "Nenhum prompt fornecido. Informe --prompt_inline, ou defina a variável de ambiente "
        "PROMPT_TEXT, ou passe o caminho do arquivo .txt como segundo argumento."
    )

def generate_prompt(prompt_template: str, transcription_text: str, audio_duration: float) -> str:
    prompt = prompt_template.replace("TRANSCRIBE", transcription_text)
    prompt = prompt.replace("DURATION", f"{audio_duration:.2f}")
    return prompt

# --------------------------
# Ollama (padrão atual)
# --------------------------
def ensure_ollama_model() -> bool:
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
        if any(model.get("name") == OLLAMA_MODEL for model in tags):
            logger.info(f"Modelo '{OLLAMA_MODEL}' já está disponível!")
            return True
        logger.info(f"Modelo '{OLLAMA_MODEL}' não encontrado, tentando baixar automaticamente...")
        pull_payload = {"name": OLLAMA_MODEL}
        pull_resp = requests.post(url_pull, json=pull_payload, timeout=600)
        pull_resp.raise_for_status()
        logger.info(f"Download do modelo '{OLLAMA_MODEL}' iniciado. Aguardando concluir...")
        for _ in range(60):
            response = requests.get(url_tags, timeout=60)
            tags = response.json().get("models", [])
            if any(model.get("name") == OLLAMA_MODEL for model in tags):
                logger.info(f"Modelo '{OLLAMA_MODEL}' agora está disponível!")
                return True
            time.sleep(5)
        logger.error(f"Não foi possível baixar o modelo '{OLLAMA_MODEL}' em tempo hábil.")
        return False
    except Exception as e:
        logger.error(f"Erro ao checar/baixar modelo '{OLLAMA_MODEL}': {e}")
        return False

def request_ollama(prompt: str) -> str:
    OLLAMA_HOSTNAME = os.getenv("OLLAMA_HOSTNAME")
    OLLAMA_PORT = os.getenv("OLLAMA_PORT")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
    OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "2400"))

    options = {
        "temperature": float(os.getenv("OLLAMA_TEMPERATURE", "0.2")),
        "top_p": float(os.getenv("OLLAMA_TOP_P", "0.9")),
        "top_k": int(os.getenv("OLLAMA_TOP_K", "40")),
        "repeat_penalty": float(os.getenv("OLLAMA_REPEAT_PENALTY", "1.1")),
        "num_ctx": int(os.getenv("OLLAMA_NUM_CTX", "8192")),
        "num_predict": int(os.getenv("OLLAMA_NUM_PREDICT", "512")),
    }

    url = f"http://{OLLAMA_HOSTNAME}:{OLLAMA_PORT}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "options": options,
        "prompt": prompt
    }
    logger.info(f"Enviando prompt para {url} (Ollama)...")
    response = requests.post(url, json=payload, timeout=OLLAMA_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    result = data.get("response", "").strip()
    logger.info(f"Resposta do Ollama: {result[:500]}{'...' if len(result) > 500 else ''}")
    return result

# --------------------------
# ChatGPT API (alternativa)
# --------------------------
def request_chatgpt(prompt: str) -> str:
    """
    Faz chamada à API de Chat Completions compatível com OpenAI.
    Variáveis de ambiente necessárias:
      - OPENAI_API_KEY (obrigatória)
      - CHATGPT_MODEL (ex.: 'gpt-4o-mini' | 'gpt-4o')
      - OPENAI_BASE_URL (opcional; padrão https://api.openai.com/v1)
      - CHATGPT_TEMPERATURE (opcional; padrão 0.2)
      - CHATGPT_TIMEOUT (opcional; padrão 240s)
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY não definido. Defina-o para usar USE_CHATGPT=true.")

    model = os.getenv("CHATGPT_MODEL", "gpt-4o-mini")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    endpoint = f"{base_url}/chat/completions"
    temperature = float(os.getenv("CHATGPT_TEMPERATURE", "0.2"))
    timeout = int(os.getenv("CHATGPT_TIMEOUT", "240"))

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Reforço mínimo de system para obedecer formato
    messages = [
        {
            "role": "system",
            "content": (
                "Você extrai cortes de vídeo. Responda ESTRITAMENTE com um array JSON de objetos "
                '{"start": <segundos>, "end": <segundos>}' " e nada mais."
            ),
        },
        {"role": "user", "content": prompt},
    ]

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "response_format": {"type": "json_object"}  # ajuda a evitar texto solto; pode retornar dict
    }

    logger.info(f"Enviando prompt para {endpoint} (ChatGPT: {model})...")
    resp = requests.post(endpoint, headers=headers, json=payload, timeout=timeout)
    try:
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"Erro HTTP ChatGPT: {resp.status_code} - {resp.text}")
        raise e

    data = resp.json()
    # Pode voltar um objeto JSON por conta do response_format. Vamos extrair texto com fallback.
    try:
        content = data["choices"][0]["message"]["content"]
        # content pode ser JSON (string JSON) ou um objeto serializado pelo servidor
        if isinstance(content, dict):
            result = json.dumps(content, ensure_ascii=False)
        else:
            result = str(content)
    except Exception:
        # fallback para formatos alternativos
        result = json.dumps(data, ensure_ascii=False)

    logger.info(f"Resposta do ChatGPT: {result[:500]}{'...' if len(result) > 500 else ''}")
    return result.strip()

# --------------------------
# Parsing do retorno
# --------------------------
def extract_json_list(text: str):
    """
    Extrai a lista JSON do texto, mesmo que haja comentários antes/depois.
    Garante lista no retorno (se vier dict, vira [dict]).
    Também remove cercas de código (```).
    """
    try:
        cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE)
        m = re.search(r'\[.*\]', cleaned, re.DOTALL)
        if m:
            obj = json.loads(m.group(0))
        else:
            # pode ter vindo um objeto {"clips":[...]} se response_format for json_object
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict) and "clips" in parsed and isinstance(parsed["clips"], list):
                obj = parsed["clips"]
            else:
                obj = parsed
    except Exception as e:
        raise ValueError(f"Não foi possível decodificar JSON dos cortes: {e}")

    if isinstance(obj, dict):
        obj = [obj]
    if not isinstance(obj, list):
        raise ValueError("Formato inválido: esperado array JSON de objetos {start, end}.")
    return obj

# --------------------------
# Main (CLI)
# --------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Detecta highlights a partir de um SRT e um prompt (arquivo ou inline)."
    )
    parser.add_argument("srt_path", help="Caminho do arquivo .srt")
    parser.add_argument("prompt_path", nargs="?", default=None,
                        help="(Opcional) Caminho do arquivo de prompt .txt")
    parser.add_argument("--prompt_inline", default=None,
                        help="(Opcional) Prompt inline (texto completo). "
                             "Se informado, ignora prompt_path e PROMPT_TEXT.")
    args = parser.parse_args()

    srt_path = args.srt_path
    prompt_path = args.prompt_path
    prompt_inline = args.prompt_inline

    logger.info(f"Lendo SRT: {srt_path}")
    transcription = read_srt_transcription(srt_path)
    duration = get_audio_duration_from_srt(srt_path)
    logger.info(f"Duração estimada: {duration:.2f} segundos")

    try:
        prompt_template = resolve_prompt_text(prompt_path, prompt_inline)
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)

    prompt = generate_prompt(prompt_template, transcription, duration)

    use_chatgpt = env_flag("USE_CHATGPT", "false")
    try:
        if use_chatgpt:
            logger.info("USE_CHATGPT=true → usando API do ChatGPT.")
            result = request_chatgpt(prompt)
        else:
            logger.info("USE_CHATGPT=false → usando Ollama local.")
            if ensure_ollama_model():
                result = request_ollama(prompt)
            else:
                logger.error("O modelo Ollama não está disponível e não pôde ser baixado.")
                sys.exit(1)
    except Exception as e:
        logger.error(f"Falha ao obter resposta do modelo: {e}")
        sys.exit(1)

    highlight_path = os.path.splitext(srt_path)[0] + ".highlight.json"
    try:
        highlight_data = extract_json_list(result)
        with open(highlight_path, "w", encoding="utf-8") as f:
            json.dump(highlight_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Highlight(s) salvo(s) em {highlight_path}")
    except Exception as e:
        logger.error(f"Não foi possível processar o resultado do modelo: {result} - erro: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
