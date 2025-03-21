document.addEventListener('DOMContentLoaded', function () {
    const socket = io();
    let isConnected = false;
    let currentDownloadTitle = null;  // Speichert den aktuellen Download-Titel

    // Verbindungsstatus
    socket.on('connect', () => {
        isConnected = true;
        console.log('✅ Mit Server verbunden');
        document.getElementById('status').innerText = '✅ Verbunden';
        document.getElementById('status').classList.remove('connecting');
    });

    socket.on('disconnect', () => {
        isConnected = false;
        console.log('❌ Verbindung zum Server getrennt');
        document.getElementById('status').innerText = '❌ Verbindung verloren';
        document.getElementById('status').classList.add('connecting');
    });

    // Datenaktualisierung vom Server
    socket.on('update', function (data) {
        updateUI(data);
    });

    // UI aktualisieren
    function updateUI(data) {
        const statusElement = document.getElementById('status');
        const progressBar = document.getElementById('overall-progress');
        const progressText = document.getElementById('progress-text');
        const cancelBtn = document.getElementById('cancel-btn');

        if (data.current.includes("Fehler")) {
            statusElement.innerHTML = `❌ ${data.current}`;
            statusElement.style.background = '#FF474710';
            progressBar.style.width = '0%';
            progressText.innerText = '0%';
            cancelBtn.style.display = 'none';
            currentDownloadTitle = null;
        } else if (data.current.includes("abgeschlossen")) {
            statusElement.innerHTML = `✅ ${data.current}`;
            statusElement.style.background = '#10A37F20';
            progressBar.style.width = '100%';
            progressText.innerText = '100%';
            cancelBtn.style.display = 'none';
            currentDownloadTitle = null;
        } else if (data.current.includes("Starte")) {
            statusElement.innerHTML = `🔄 ${data.current}`;
            statusElement.style.background = 'var(--bg-panel)';
            progressBar.style.width = data.progress;
            progressText.innerText = data.progress;
            currentDownloadTitle = data.current.split(': ')[1];
            cancelBtn.style.display = 'inline-block';
        } else {
            statusElement.innerHTML = `🔄 ${data.current}`;
            statusElement.style.background = 'var(--bg-panel)';
            progressBar.style.width = data.progress;
            progressText.innerText = data.progress;
        }

        const queueDiv = document.getElementById('queue');
        queueDiv.innerHTML = data.queue.length > 0
            ? data.queue.map(item => `
                <div class="queue-item">
                    <span class="url">${item.url}</span>
                    <span class="options">${JSON.stringify(item.options)}</span>
                </div>`
            ).join('')
            : "<div class='empty'>⏳ Keine ausstehenden Downloads</div>";

        const logDiv = document.getElementById('log');
        logDiv.innerHTML = data.logs.map(log => `
            <div class="log-entry">
                <span class="title">${log.title}</span>
                <span class="timestamp">${log.timestamp}</span>
            </div>`
        ).join('');
    }

    function convertShortsToNormal(url) {
        return url.replace("youtube.com/shorts/", "youtube.com/watch?v=");
    }

    function processUrls(urls) {
        return urls.split(',')
            .map(u => u.trim())
            .filter(u => u !== "")
            .map(convertShortsToNormal);
    }

    // Download-Button Event
    const downloadBtn = document.getElementById('download-btn');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', function () {
            const urls = document.getElementById('video-url').value;
            if (!urls) {
                alert("Bitte gib eine YouTube-URL ein!");
                return;
            }
            const cleanedUrls = processUrls(urls);

            // Alle Checkboxen auslesen
            const mp4Checkbox = document.getElementById('download-mp4');
            const wavCheckbox = document.getElementById('download-wav');
            const transcriptCheckbox = document.getElementById('download-transcript');
            const imageCheckbox = document.getElementById('download-image');

            // Options-Objekt erstellen
            const options = {
                mp4: mp4Checkbox.checked,
                wav: wavCheckbox.checked,
                transcript: transcriptCheckbox.checked,
                thumbnail: imageCheckbox.checked
            };

            cleanedUrls.forEach(url => {
                fetch('http://localhost:8080/api/download', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: url, options: options })
                })
                    .then(response => {
                        if (!response.ok) {
                            return response.json().then(err => Promise.reject(err.error));
                        }
                        return response.json();
                    })
                    .then(data => {
                        console.log("Download gestartet:", data);
                        showToast("Download erfolgreich gestartet!", "success");
                    })
                    .catch(err => {
                        console.error("Fehler beim Starten des Downloads:", err);
                        showToast(`Fehler: ${err.message || err}`, "error");
                    });
            });
        });
    } else {
        console.error("Download-Button nicht gefunden!");
    }

    // Abbrechen-Button Event
    const cancelBtn = document.getElementById('cancel-btn');
    cancelBtn.addEventListener('click', function () {
        if (currentDownloadTitle) {
            fetch('http://localhost:8080/api/cancel', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: currentDownloadTitle })
            })
                .then(response => {
                    if (!response.ok) {
                        return response.json().then(err => Promise.reject(err.error));
                    }
                    return response.json();
                })
                .then(data => {
                    console.log("Download abgebrochen:", data);
                    showToast("Download abgebrochen!", "success");
                })
                .catch(err => {
                    console.error("Fehler beim Abbrechen des Downloads:", err);
                    showToast(`Fehler: ${err.message || err}`, "error");
                });
        }
    });

    function showToast(message, type) {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerText = message;
        document.body.appendChild(toast);
        setTimeout(() => { toast.remove(); }, 3000);
    }

    fetch('http://localhost:8080/api/status')
        .then(response => response.json())
        .then(data => updateUI(data))
        .catch(err => {
            console.error("Fehler beim Abrufen des Status:", err);
            showToast("Fehler beim Abrufen des Status", "error");
        });
});