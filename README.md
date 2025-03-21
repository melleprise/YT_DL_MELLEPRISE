```
# YouTube Downloader with Chrome Extension

## Übersicht
YouTube Downloader, der MP4, WAV, Transkript und Thumbnail aus YouTube-Videos herunterlädt. Die Anwendung läuft in Docker (Flask API) und wird über eine Chrome Extension gesteuert.

## Installation

### Docker Setup
1. **Voraussetzungen:** Docker und Docker Compose installieren.
2. **Repository klonen:**
   ```
   git clone <repository-url>
   cd <repository-folder>
   ```
3. **Container starten:**
   ```
   docker-compose up --build
   ```
   Der Server ist dann unter [http://localhost:8080](http://localhost:8080) erreichbar.

### Chrome Extension Setup
1. In Chrome zu `chrome://extensions/` navigieren.
2. Entwicklermodus aktivieren.
3. Auf "Entpackte Erweiterung laden" klicken und den Ordner `YT_DL_CHROME_EX` auswählen.

## Benutzung

### Server-API
- **Status abrufen:** [http://localhost:8080/api/status](http://localhost:8080/api/status)
- **Download starten:** Sende eine POST-Anfrage an [http://localhost:8080/api/download](http://localhost:8080/api/download) mit folgendem JSON:
  ```
  {
    "url": "https://www.youtube.com/watch?v=VIDEO_ID",
    "options": {
      "mp4": true,
      "wav": true,
      "transcript": true,
      "thumbnail": true
    }
  }
  ```

### Chrome Extension
1. Ein YouTube-Video öffnen.
2. Auf das Extension-Symbol klicken.
3. Gewünschte Optionen auswählen (Video, Audio, Transkript, Thumbnail).
4. "Start Download" klicken – die Anfrage wird an den Server gesendet.

## Troubleshooting
- **Server nicht erreichbar:** Sicherstellen, dass Docker läuft und der Container aktiv ist.
- **Keine Option gewählt:** Mindestens eine Download-Option auswählen.
- **Fragen/Probleme:** Im Issues-Bereich des Repositories melden.
```