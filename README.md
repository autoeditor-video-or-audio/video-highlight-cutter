# Audio Highlight Cutter

Um webapp simples e prático para **upload de vídeos (.mp4)**, extração automática de **highlights** (momentos importantes) e **download/visualização** dos cortes diretamente pelo navegador.

---

## 🚀 Como funciona

1. **Upload:** Envie um vídeo `.mp4` pela interface web.
2. **Processamento:** O sistema extrai o áudio, faz transcrição automática (Whisper), detecta os highlights via IA e corta os trechos relevantes.
3. **Acompanhamento em tempo real:** Os highlights aparecem na página para assistir, baixar ou compartilhar enquanto o processamento ocorre.

---

## 🛠️ Principais Tecnologias

- **Python FastAPI** (backend web)
- **MoviePy** & **Whisper** (processamento e transcrição)
- **Ollama** (IA para seleção dos melhores highlights)
- **Jinja2** (frontend dinâmico)
- **TailwindCSS** (layout responsivo)
- **JavaScript** (atualização dinâmica de status)

---

## 👨‍💻 Como rodar localmente

```bash
# Instale as dependências Python
pip install -r requirements.txt

# Inicie o servidor web
uvicorn webapp:app --reload --host 0.0.0.0 --port 8000

# Abra o navegador em
http://localhost:8000
```

## 🐳 Rodando via Docker

```bash
# 1. Crie a rede docker (apenas na primeira vez)
docker network create app-network

# 2. Suba todos os serviços (webapp, Whisper e Ollama)
docker compose up --build -d

# 3. Acesse normalmente em
http://localhost:8000
```

> **Obs:** O processamento usa IA e pode demorar alguns minutos conforme o vídeo.

---

## 📂 Estrutura do Projeto

- Os arquivos processados ficam na pasta `processed/`
- Highlights podem ser baixados em `.mp4`
- Transcrições e cortes intermediários também são salvos

---

## ⚡ Exemplos de comandos úteis

```bash
# Extrai highlights do vídeo usando um arquivo de legendas já transcrito:
python detect_highlight.py seu_video.srt prompt_detect_highlight.txt
# Gera: seu_video.highlight.json (lista de cortes sugeridos)

# Classifica os cortes usando IA:
python classify_segments.py seu_video.srt seu_video.highlight.json prompt_classify.txt
# Gera: seu_video.highlight.classified.json

# Filtra os melhores highlights:
python filter_highlights.py seu_video.highlight.classified.json seu_video.highlight.filtered.json

# Corta os highlights finais do vídeo original:
python cut_highlight.py seu_video.mp4 seu_video.highlight.filtered.json
# Gera arquivos highlight: seu_video_highlight1.mp4, etc.
```

## 🐳 docker-compose.yaml (resumido)

```yaml
services:
  video-highlight-cutter:
    build: .
    container_name: video-highlight-cutter
    env_file:
      - .env
    ports:
      - "8000:8000"
    restart: always
    tty: true
    stdin_open: true
    volumes:
      - ./app:/app
    networks:
      - default
    working_dir: /app
    depends_on:
      - whisper
      - ollama

  whisper:
    image: onerahmet/openai-whisper-asr-webservice:v1.9.1
    container_name: whisper
    restart: unless-stopped
    environment:
      - ASR_MODEL=turbo
      - ASR_ENGINE=openai_whisper
    ports:
      - "9000:9000"
    volumes:
      - cache-whisper:/root/.cache
    networks:
      - default
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000"]
      interval: 10s
      timeout: 5s
      retries: 10

  ollama:
    image: ollama/ollama:0.10.1
    container_name: ollama
    restart: always
    ports:
      - "11434:11434"
    volumes:
      - ollama:/root/.ollama
    environment:
      - OLLAMA_MODELS=llama3.2:3b
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434"]
      interval: 10s
      timeout: 5s
      retries: 10
    networks:
      - default

networks:
  default:
    external: true
    name: app-network

volumes:
  cache-whisper:
  ollama:
```

## 🐍 Dockerfile (resumido)

```dockerfile
FROM python:3.11-slim

RUN apt-get -y update && apt-get -y upgrade && apt-get install -y --no-install-recommends libmediainfo0v5 libmediainfo-dev ffmpeg
RUN python -m pip install --upgrade pip
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ./app .
EXPOSE 8000
CMD ["uvicorn", "webapp:app", "--host", "0.0.0.0", "--port", "8000"]
```

## ℹ️ Observações

- Os highlights aparecem automaticamente enquanto o processamento ocorre.
- Todos os arquivos processados ficam organizados na pasta `processed/`.
- O sistema pode baixar o modelo de IA do Ollama automaticamente, se necessário.

---

## 🤝 Contribua!

Achou algum bug, tem uma sugestão ou quer contribuir?  
Abra uma issue ou PR!

---
