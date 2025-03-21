FROM python:3.11

# Installiere Systempakete
RUN apt-get update && apt-get install -y \
    ffmpeg \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Setze Umgebungsvariablen für ffmpeg
ENV FFMPEG_PATH=/usr/bin/ffmpeg
ENV FFPROBE_PATH=/usr/bin/ffprobe
ENV PYTHONPYCACHEPREFIX=/__pycache__

WORKDIR /app
COPY . /app

# Upgrade pip und installiere Python-Abhängigkeiten
RUN pip install --upgrade pip && \
    pip install --default-timeout=100 --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir watchdog && \
    pip install --no-cache-dir "yt-dlp[default,curl-cffi]"

# Erstelle Download-Ordner
RUN mkdir -p /downloads
ENV DOWNLOAD_PATH=/downloads
ENV YDL_CONFIG_DIR=/downloads
ENV YDL_OUTPUT_TEMPLATE=/downloads/%(title)s.%(ext)s

# Produktionsstart: Verwende watchmedo, um den Server neu zu starten, wenn Python-Code geändert wird.
CMD ["watchmedo", "auto-restart", "--patterns=*.py", "--recursive", "--", "python", "server.py"]
