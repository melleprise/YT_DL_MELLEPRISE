# **YouTube High-Quality Downloader | Nginx & Python & Chrome-Erweiterung**

📥 **Ein leistungsstarker YouTube-Downloader** für **MP4 & WAV in hoher Qualität** sowie das **Transkript**, falls verfügbar.  
🔗 Die Steuerung erfolgt über eine **Chrome-Erweiterung**, die ein Signal an einen **Nginx-Container** sendet, der den Download über einen **Python-Container in einer Docker-Umgebung** abwickelt.

---

## **🔧 Host-Konfiguration setzen**

Füge diese Zeile ein, damit **youtube.local** als Domain erreichbar ist:

```sh
grep -qxF "127.0.0.1 youtube.local" /etc/hosts || echo "127.0.0.1 youtube.local" | sudo tee -a /etc/hosts
```

Oder öffne die `hosts`-Datei manuell:

```sh
sudo vim /etc/hosts
```

Füge folgende Zeile hinzu und speichere:

```
127.0.0.1 youtube.local
```

---

## **🛠 Installation von Homebrew und Docker im CLI-Modus**

Führe folgende Befehle im Terminal aus:

```sh
# Homebrew installieren
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Docker CLI installieren
brew install docker

# Comida installieren (falls erforderlich)
brew install comida
```

---

## **manueller test:** gehe in das verzeichnis um das setup zu testen
```sh
# gehen zu dem pfad
cd /pathto/YT_DL_MELLEPRISE

# starte docker
docker-compose up
```

🔥 **Jetzt kannst du die Anwendung starten und YouTube-Videos in bester Qualität herunterladen!** 🚀  

💡 **Fragen oder Probleme? Lass es mich wissen!** 😃
docker compose down --remove-orphans && docker network prune -f && docker compose up -build

docker compose down --remove-orphans && docker system prune -f && docker compose build --no-cache && docker compose up

docker compose down && docker system prune -f && docker compose build --no-cache && docker compose up

docker-compose down && docker-compose up --build

docker compose build --no-cache



https://www.youtube.com/watch?v=NBAyZRp-SG0

docker-compose build

curl -X POST http://localhost:8081/api/download \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.youtube.com/watch?v=NBAyZRp-SG0", "format": "video"}'


yt-dlp -f "bestvideo[ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/best" --merge-output-format mp4 "https://www.youtube.com/shorts/NBAyZRp-SG0"



