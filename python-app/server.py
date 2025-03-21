import logging
import json
import os
import sys
from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO
from flask_cors import CORS
from youtube_downloader_logic import process_queue, add_to_queue, initialize_socketio, cancel_download
from utils import save_downloads
from globals import download_status, currently_downloading
from threading import Lock
from yt_dlp import YoutubeDL  # Import hinzufügen für Titel-Extraktion

LOG_DIR = os.path.expanduser("/downloads/logs")
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logger(name, log_file):
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        logger.setLevel(logging.DEBUG)
        file_handler = logging.FileHandler(os.path.join(LOG_DIR, log_file))
        file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logger.addHandler(file_handler)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logger.addHandler(console_handler)
    return logger

server_logger = setup_logger("server_logger", "server.log")
download_logger = setup_logger("download_logger", "download.log")

app = Flask(__name__, static_folder='status')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)
initialize_socketio(socketio)
download_lock = Lock()

@app.route('/')
def serve_index():
    return send_from_directory('status', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('status', filename)

@app.route('/api/download', methods=['POST'])
def download_video():
    data = request.json
    server_logger.info(f"Download-Anfrage erhalten:\n{json.dumps(data, indent=2)}")
    
    url = data.get("url")
    options = data.get("options")
    if not url or options is None:
        server_logger.warning("⚠️ Download-Anfrage ohne URL oder Optionen erhalten")
        return jsonify({"error": "URL und Optionen müssen angegeben werden!"}), 400

    # Titel des Videos extrahieren
    with YoutubeDL({'quiet': True}) as ydl:
        info_dict = ydl.extract_info(url, download=False)  # Nur Info abrufen, nicht downloaden
        title = info_dict.get('title', 'Unbekannt')  # Titel holen, Fallback ist "Unbekannt"

    server_logger.info(f"📥 Download angefordert: {url} mit Optionen: {options}")
    add_to_queue(url, options)  # Download zur Warteschlange hinzufügen
    
    with download_lock:
        if currently_downloading is None:
            process_queue()  # Warteschlange starten, falls nichts läuft

    return jsonify({
        "message": "Download zur Warteschlange hinzugefügt",
        "url": url,
        "options": options,
        "title": title  # Titel in der Antwort hinzufügen
    }), 200

@app.route('/api/clear-history', methods=['POST'])
def clear_history():
    server_logger.info("🧹 Download-Verlauf wird gelöscht...")
    download_status["logs"].clear()
    download_status["queue"].clear()
    save_downloads()
    socketio.emit('update', download_status)
    return jsonify({"message": "Download-Verlauf wurde gelöscht!"}), 200

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify(download_status)

@app.route('/api/cancel', methods=['POST'])
def cancel_download_route():
    data = request.get_json()
    title = data.get('title')
    if not title:
        return jsonify({"error": "Kein Titel angegeben"}), 400
    if cancel_download(title):
        return jsonify({"message": f"Download abgebrochen für: {title}"}), 200
    return jsonify({"error": "Kein aktiver Download mit diesem Titel gefunden"}), 404

@app.errorhandler(404)
def not_found(error):
    server_logger.warning(f"❌ 404 Fehler: {request.url} nicht gefunden")
    return jsonify({"error": "Nicht gefunden", "url": request.url}), 404

if __name__ == "__main__":
    server_logger.info("🚀 Starte den Flask-Server auf Port 8080")
    socketio.run(app, host="0.0.0.0", port=8080, allow_unsafe_werkzeug=True)