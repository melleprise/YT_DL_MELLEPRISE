from queue import Queue

download_status = {
    "current": "Warten auf Download...",
    "progress": "0%",
    "queue": [],
    "logs": []
}

download_queue = Queue()
currently_downloading = None
