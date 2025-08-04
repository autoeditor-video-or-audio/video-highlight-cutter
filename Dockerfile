FROM python:3.11-slim

# Instala ffmpeg (necessário para o moviepy manipular áudio)
# Atualizar e instalar ffmpeg para processamento de vídeo
RUN apt-get -y update && apt-get -y upgrade && apt-get install -y --no-install-recommends libmediainfo0v5 libmediainfo-dev ffmpeg

# Atualizar pip e instalar dependências Python
RUN python -m pip install --upgrade pip

# Cria o diretório de trabalho
WORKDIR /app

# Copiar o arquivo requirements.txt e instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia os arquivos para o container
COPY ./app .

EXPOSE 8000
CMD ["uvicorn", "webapp:app", "--host", "0.0.0.0", "--port", "8000"]


# # Define entrypoint padrão, pode ser sobrescrito no docker-compose
# ENTRYPOINT ["python", "extrai_audio.py"]

# python detect_highlight.py livee.srt prompt_detect_highlight.txt
# Gera: livee.highlight.json (lista de cortes ótimos)

### BKP
# # # python auto_segment_srt.py livee.srt
# # # Gera: seu_video.highlight.json

# python classify_segments.py livee.srt livee.highlight.json prompt_classify.txt
# Gera: seu_video.highlight.classified.json


# python filter_highlights.py livee.highlight.classified.json livee.highlight.filtered.json
# Gera: seu_video.highlight.filtered.json

# python cut_highlight.py livee.mp4 livee.highlight.filtered.json
# Gera vários arquivos highlight!
# Gera: seu_video_highlightX.mp4