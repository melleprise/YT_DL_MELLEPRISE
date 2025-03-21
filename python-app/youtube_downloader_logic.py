import subprocess
import re
import os
import logging
from threading import Thread, Lock, Event
from datetime import datetime
from pathlib import Path
import glob
from yt_dlp import YoutubeDL
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from utils import remove_ansi_codes, save_downloads
from globals import download_status, download_queue, currently_downloading

DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_PATH", "/downloads"))
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

socketio = None
progress_lock = Lock()
active_download_threads = {}

def emit_update():
    if socketio:
        socketio.emit('update', download_status)

def initialize_socketio(socket_instance):
    global socketio
    socketio = socket_instance

def sanitize_filename(filename):
    return "".join(c if c.isalnum() or c in " ._-()" else "_" for c in filename).replace(" ", "_").rstrip('.')

def extract_video_id(url):
    match = re.search(r"v=([a-zA-Z0-9_-]+)", url) or re.search(r"shorts/([a-zA-Z0-9_-]+)", url)
    if match:
        return match.group(1)
    raise ValueError(f"Could not extract video ID from URL: {url}")

def get_storage_paths(title):
    folder_path = DOWNLOAD_DIR / title
    folder_path.mkdir(parents=True, exist_ok=True)
    return {
        "folder": folder_path,
        "video": folder_path / "video.mp4",
        "audio": folder_path / "audio.wav",
        "transcript": folder_path / "transkript.txt",
        "thumbnail": folder_path / "thumbnail.png"
    }

def check_existing_files(title, options):
    paths = get_storage_paths(title)
    existing = {
        "mp4": paths["video"].exists() if options.get("mp4") else True,
        "wav": paths["audio"].exists() if options.get("wav") else True,
        "transcript": paths["transcript"].exists() if options.get("transcript") else True,
        "thumbnail": paths["thumbnail"].exists() if options.get("thumbnail") else True
    }
    return all(existing.values())

def get_best_format(info, codec, is_audio=False):
    formats = info.get('formats', [])
    if is_audio:
        filtered = [f for f in formats if f.get('acodec') and f.get('acodec').startswith(codec) and f.get('vcodec') == 'none']
    else:
        filtered = [f for f in formats if f.get('vcodec') and f.get('vcodec').startswith(codec) and f.get('acodec') == 'none']
    if not filtered:
        raise ValueError(f"Kein Format mit Codec {codec} gefunden")
    filtered.sort(key=lambda x: x.get('filesize') or x.get('tbr', 0), reverse=True)
    best_format = filtered[0]
    logging.info(f"Bestes Format für {codec}: {best_format['format_id']} (Größe: {best_format.get('filesize', 'unbekannt')})")
    return best_format['format_id']

def start_download(url, options):
    global currently_downloading
    logging.info(f"🟢 Starte Download: {url} mit Optionen: {options}")
    try:
        with YoutubeDL({'quiet': True}) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            title = sanitize_filename(info_dict.get('title', 'Unbekannt'))
        paths = get_storage_paths(title)
        total_steps = 0
        if options.get("mp4"):
            total_steps += 50
            total_steps += 20
        if options.get("wav"):
            total_steps += 10
        if options.get("transcript"):
            total_steps += 10
        if options.get("thumbnail"):
            total_steps += 10
        current_progress = 0
        download_status["progress"] = "0%"
        download_status["current"] = f"Starte Download: {title}"
        currently_downloading = title
        emit_update()
        download_performed = False
        best_audio_format = None
        best_video_format = None
        if options.get("mp4") or options.get("wav"):
            best_audio_format = get_best_format(info_dict, 'mp4a.40.2', is_audio=True)
        if options.get("mp4"):
            try:
                best_video_format = get_best_format(info_dict, 'avc1', is_audio=False)
            except ValueError:
                best_video_format = "bestvideo[ext=mp4]"
        if options.get("mp4"):
            if not paths["video"].exists():
                download_video_audio(url, title, paths, options, total_steps, current_progress, best_video_format, best_audio_format)
                current_progress += 50
                download_status["progress"] = f"{min((current_progress / total_steps * 100), 100):.2f}%"
                emit_update()
                if not check_video_codec(paths["video"]):
                    convert_video_to_h264(paths["video"], total_steps, current_progress)
                    current_progress += 20
                    download_status["progress"] = f"{min((current_progress / total_steps * 100), 100):.2f}%"
                    emit_update()
                download_performed = True
            else:
                logging.info(f"⚠️ MP4-Download übersprungen für '{title}': Datei '{paths['video']}' existiert bereits")
        else:
            logging.info(f"ℹ️ MP4-Download nicht angefordert für '{title}'")
        if options.get("wav"):
            if not paths["audio"].exists():
                if options.get("mp4") and paths["video"].exists():
                    extract_audio_to_wav(paths["video"], paths["audio"])
                else:
                    download_audio_only(url, title, paths, total_steps, current_progress, best_audio_format)
                current_progress += 10
                download_status["progress"] = f"{min((current_progress / total_steps * 100), 100):.2f}%"
                emit_update()
                download_performed = True
            else:
                logging.info(f"⚠️ WAV-Download übersprungen für '{title}': Datei '{paths['audio']}' existiert bereits")
        else:
            logging.info(f"ℹ️ WAV-Download nicht angefordert für '{title}'")
        if options.get("transcript"):
            if not paths["transcript"].exists():
                download_transcript(url, title, paths["transcript"])
                current_progress += 10
                download_status["progress"] = f"{min((current_progress / total_steps * 100), 100):.2f}%"
                emit_update()
                download_performed = True
            else:
                logging.info(f"⚠️ Transkript-Download übersprungen für '{title}': Datei '{paths['transcript']}' existiert bereits")
        else:
            logging.info(f"ℹ️ Transkript-Download nicht angefordert für '{title}'")
        if options.get("thumbnail"):
            if not paths["thumbnail"].exists():
                download_thumbnail(url, title, paths["thumbnail"])
                current_progress += 10
                download_status["progress"] = f"{min((current_progress / total_steps * 100), 100):.2f}%"
                emit_update()
                download_performed = True
            else:
                logging.info(f"⚠️ Thumbnail-Download übersprungen für '{title}': Datei '{paths['thumbnail']}' existiert bereits")
        else:
            logging.info(f"ℹ️ Thumbnail-Download nicht angefordert für '{title}'")
        if download_performed:
            logging.info(f"✅ Download abgeschlossen: {title}")
            download_status["current"] = f"Download abgeschlossen: {title}"
            download_status["progress"] = "100%"
        else:
            logging.info(f"ℹ️ Kein Download durchgeführt für '{title}': Alle Dateien existieren bereits")
            download_status["current"] = f"Download übersprungen: {title}"
            download_status["progress"] = "100%"
    except Exception as e:
        logging.error(f"❌ Fehler beim Download von {title}: {str(e)}")
        download_status["current"] = f"Fehler beim Download von {title}: {str(e)}"
        download_status["progress"] = "0%"
        emit_update()
        raise
    finally:
        with progress_lock:
            download_status["queue"] = [item for item in download_status["queue"] if item["url"] != url or item["options"] != options]
        currently_downloading = None
        download_status["logs"].append({
            "title": title,
            "timestamp": datetime.now().strftime("%d.%m.%Y, %H:%M:%S")
        })
        save_downloads()
        emit_update()
        process_queue()

def download_video_audio(url, title, paths, options, total_steps, current_progress, video_format, audio_format):
    stop_event = Event()
    ydl_opts = {
        'format': f"{video_format}+{audio_format}",
        'outtmpl': str(paths["video"]),
        'merge_output_format': 'mp4',
        'progress_hooks': [lambda d: progress_hook(d, stop_event, total_steps, current_progress)],
        'quiet': False,
        'no_warnings': False,
        'fragment_retries': 10,
        'retries': 10
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        logging.info(f"✅ MP4 heruntergeladen: {paths['video']}")
    except Exception as e:
        logging.error(f"❌ Fehler beim Video-Download: {str(e)}")
        raise

def download_audio_only(url, title, paths, total_steps, current_progress, audio_format):
    stop_event = Event()
    temp_audio = paths["folder"] / "temp_audio.m4a"
    ydl_opts = {
        'format': audio_format,
        'outtmpl': str(temp_audio),
        'progress_hooks': [lambda d: progress_hook(d, stop_event, total_steps, current_progress)],
        'quiet': False,
        'no_warnings': False,
        'fragment_retries': 10,
        'retries': 10
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        cmd = f'ffmpeg -y -i "{temp_audio}" -vn -acodec pcm_s16le -ar 44100 "{paths["audio"]}"'
        subprocess.run(cmd, shell=True, check=True)
        logging.info(f"✅ Audio als WAV heruntergeladen: {paths['audio']}")
    except Exception as e:
        logging.error(f"❌ Fehler beim Audio-Download: {str(e)}")
        raise
    finally:
        if temp_audio.exists():
            os.remove(temp_audio)

def download_transcript(url, title, transcript_path):
    video_id = extract_video_id(url)
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['de', 'en'])
        with open(transcript_path, "w", encoding="utf-8") as file:
            for item in transcript:
                file.write(f"{item['start']} - {item['text']}\n")
        logging.info(f"✅ Transkript gespeichert: {transcript_path}")
    except (TranscriptsDisabled, NoTranscriptFound):
        logging.warning(f"⚠️ Kein Transkript verfügbar für {title}")
    except Exception as e:
        logging.error(f"❌ Fehler beim Transkript-Download: {e}")

def download_thumbnail(url, title, thumbnail_path):
    ydl_opts = {
        'skip_download': True,
        'writethumbnail': True,
        'outtmpl': str(thumbnail_path).replace(".png", ""),
        'postprocessors': [{'key': 'FFmpegThumbnailsConvertor', 'format': 'png'}]
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        logging.info(f"✅ Thumbnail gespeichert: {thumbnail_path}")
    except Exception as e:
        logging.error(f"❌ Fehler beim Thumbnail-Download: {str(e)}")

def check_video_codec(video_path):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name", "-of", "csv=p=0", str(video_path)],
            capture_output=True, text=True
        )
        return result.stdout.strip() == "h264"
    except Exception as e:
        logging.error(f"Fehler bei der Codec-Überprüfung: {e}")
        return False

def convert_video_to_h264(input_path, total_steps, current_progress):
    temp_path = input_path.with_suffix(".converted.mp4")
    progress_file = input_path.with_suffix(".progress")
    cmd = [
        "ffmpeg", "-i", str(input_path), "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "23", "-c:a", "aac", "-b:a", "128k", "-progress", str(progress_file),
        str(temp_path), "-y"
    ]
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        duration = None
        while process.poll() is None:
            if progress_file.exists():
                with open(progress_file, 'r') as f:
                    lines = f.readlines()
                    for line in lines:
                        if "out_time_ms=" in line:
                            time_ms = int(line.split("=")[1].strip())
                            time = time_ms / 1000000
                            if duration is None:
                                result = subprocess.run(
                                    ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                     "-of", "default=noprint_wrappers=1:nokey=1", str(input_path)],
                                    capture_output=True, text=True
                                )
                                duration = float(result.stdout.strip())
                            if duration:
                                conversion_percent = (time / duration) * 100
                                overall_percent = min((current_progress + (conversion_percent / 100 * 20)) / total_steps * 100, 100)
                                download_status["progress"] = f"{overall_percent:.2f}%"
                                emit_update()
        if process.returncode == 0:
            os.replace(temp_path, input_path)
            logging.info(f"✅ Video in H.264 umgewandelt: {input_path}")
        else:
            raise Exception("Konvertierung fehlgeschlagen")
    except Exception as e:
        logging.error(f"❌ Fehler bei der Konvertierung von {input_path}: {str(e)}")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise

def extract_audio_to_wav(input_path, output_path):
    cmd = f'ffmpeg -y -i "{input_path}" -vn -acodec pcm_s16le -ar 44100 "{output_path}"'
    try:
        subprocess.run(cmd, shell=True, check=True)
        logging.info(f"✅ Audio extrahiert als WAV: {output_path}")
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Fehler beim Extrahieren des Audios: {e}")
        raise

last_progress = 0

def progress_hook(d, stop_event, total_steps, current_progress):
    global last_progress
    if d['status'] == 'downloading':
        total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 1)
        downloaded_bytes = d.get('downloaded_bytes', 0)
        audio_or_video_percent = min((downloaded_bytes / total_bytes) * 100, 100)
        if total_steps == 10:
            overall_percent = audio_or_video_percent
        else:
            overall_percent = min((current_progress + (audio_or_video_percent / 100 * 50)) / total_steps * 100, 100)
        if abs(overall_percent - last_progress) >= 1:
            download_status["progress"] = f"{overall_percent:.2f}%"
            last_progress = overall_percent
            emit_update()
    elif d['status'] == 'finished':
        if total_steps == 10:
            overall_percent = 100
        else:
            overall_percent = min((current_progress + 50) / total_steps * 100, 100)
        download_status["progress"] = f"{overall_percent:.2f}%"
        last_progress = overall_percent
        emit_update()

def process_queue():
    if not download_queue.empty() and currently_downloading is None:
        next_item = download_queue.get()
        Thread(target=start_download, args=(next_item["url"], next_item["options"])).start()

def add_to_queue(url, options):
    default_options = {"mp4": False, "wav": False, "transcript": False, "thumbnail": False}
    for key, default in default_options.items():
        options.setdefault(key, default)
    try:
        with YoutubeDL({'quiet': True}) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            title = sanitize_filename(info_dict.get('title', 'Unbekannt'))
    except Exception as e:
        logging.error(f"❌ Fehler beim Extrahieren des Titels für {url}: {str(e)}")
        return
    if check_existing_files(title, options):
        logging.info(f"Alle gewünschten Dateien für '{title}' existieren bereits, überspringe Download.")
        download_status["logs"].append({
            "title": title,
            "timestamp": datetime.now().strftime("%d.%m.%Y, %H:%M:%S"),
            "message": "Bereits heruntergeladen"
        })
        emit_update()
        return
    item = {"url": url, "options": options}
    if item not in download_status["queue"]:
        download_status["queue"].append(item)
        download_queue.put(item)
        if currently_downloading is None:
            process_queue()
    else:
        logging.info(f"Duplicate entry skipped: {url} with options {options}")

def cancel_download(title):
    if title in active_download_threads:
        active_download_threads[title].set()
        logging.info(f"🔴 Download abgebrochen für: {title}")
        return True
    return False

if __name__ == "__main__":
    print("Dieses Skript sollte als Modul verwendet werden. Verwende die API (/api/download) zum Starten eines Downloads.")
