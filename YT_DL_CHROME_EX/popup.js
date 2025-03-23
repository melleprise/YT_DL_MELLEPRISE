document.addEventListener('DOMContentLoaded', function () {
  const downloadBtn = document.getElementById('download-btn');
  const mp4Checkbox = document.getElementById('download-mp4');
  const wavCheckbox = document.getElementById('download-wav');
  const transcriptCheckbox = document.getElementById('download-transcript');
  const imageCheckbox = document.getElementById('download-image');
  const statusMsg = document.getElementById('status-msg');

  function saveOptions() {
    const options = {
      mp4: mp4Checkbox.checked,
      wav: wavCheckbox.checked,
      transcript: transcriptCheckbox.checked,
      thumbnail: imageCheckbox.checked
    };
    localStorage.setItem('downloadOptions', JSON.stringify(options));
  }

  const savedOptions = localStorage.getItem('downloadOptions');
  if (savedOptions) {
    const options = JSON.parse(savedOptions);
    mp4Checkbox.checked = options.mp4;
    wavCheckbox.checked = options.wav;
    transcriptCheckbox.checked = options.transcript;
    imageCheckbox.checked = options.thumbnail;
  }

  [mp4Checkbox, wavCheckbox, transcriptCheckbox, imageCheckbox].forEach(checkbox => {
    checkbox.addEventListener('change', saveOptions);
  });

  downloadBtn.addEventListener('click', function () {
    // Button sofort deaktivieren und grau machen
    downloadBtn.classList.add('disabled');
    downloadBtn.disabled = true;

    chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
      const activeTab = tabs[0];
      if (activeTab && activeTab.url) {
        const options = JSON.parse(localStorage.getItem('downloadOptions') || '{"mp4":false,"wav":false,"transcript":false,"thumbnail":false}');

        if (!options.mp4 && !options.wav && !options.transcript && !options.thumbnail) {
          statusMsg.textContent = "Bitte wähle mindestens eine Download-Option aus.";
          setTimeout(() => window.close(), 2000); // Schließt nach 2 Sekunden
          return;
        }

        fetch('http://localhost:8080/api/download', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: activeTab.url, options: options })
        })
          .then(response => {
            if (!response.ok) throw new Error(`Serverfehler: ${response.status}`);
            return response.json();
          })
          .then(data => {
            if (data.error) throw new Error(data.error);
            console.log("Download gestartet:", data);
            statusMsg.textContent = "Download gestartet: " + (data.title || "unbekannt");
            setTimeout(() => window.close(), 2000); // Schließt nach 2 Sekunden
          })
          .catch(err => {
            console.error("Fehler beim Download:", err);
            if (err.message.includes("Failed to fetch")) {
              // Server nicht erreichbar (Netzwerkfehler)
              statusMsg.textContent = "Fehler: Server nicht erreichbar";
              downloadBtn.classList.remove('disabled'); // Button wieder aktivieren
              downloadBtn.disabled = false;
            } else {
              // Server erreichbar, aber Fehler in Antwort
              statusMsg.textContent = "Fehler: " + err.message;
              setTimeout(() => window.close(), 2000); // Schließt nach 2 Sekunden
            }
          });
      } else {
        statusMsg.textContent = "Kein aktiver Tab gefunden.";
        setTimeout(() => window.close(), 2000); // Schließt nach 2 Sekunden
      }
    });
  });
});