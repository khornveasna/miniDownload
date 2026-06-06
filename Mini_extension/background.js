const SERVER_URL = "http://127.0.0.1:8765/add";
const PING_URL = "http://127.0.0.1:8765/ping";

let isAppRunning = false;

// Periodically check if the desktop app is running
async function checkAppRunning() {
  try {
    const res = await fetch(PING_URL);
    isAppRunning = res.ok;
  } catch (err) {
    isAppRunning = false;
  }
}

// Check every 3 seconds
checkAppRunning();
setInterval(checkAppRunning, 3000);

// File extensions that we want to intercept
const INTERCEPT_EXTENSIONS = /\.(zip|rar|7z|tar|gz|exe|msi|pdf|mp3|mp4|mkv|avi|mov|dmg|iso|torrent|docx|xlsx|pptx)$/i;

chrome.downloads.onCreated.addListener(async (downloadItem) => {
  // If the app is not running, let Chrome download it normally
  if (!isAppRunning) {
    return;
  }

  // Avoid intercepting local server downloads
  if (downloadItem.url.startsWith("http://127.0.0.1") || downloadItem.url.startsWith("http://localhost")) {
    return;
  }

  // Get download pathname or filename to check extension
  const url = downloadItem.url;
  const filename = downloadItem.filename || "";
  const pathname = new URL(url).pathname;

  // Intercept if the extension matches
  if (INTERCEPT_EXTENSIONS.test(pathname) || INTERCEPT_EXTENSIONS.test(filename)) {
    // Cancel the chrome download
    chrome.downloads.cancel(downloadItem.id);

    // Get the base filename
    let cleanName = filename.split(/[\\/]/).pop() || "Download from Browser";

    // Send it to Mini Download
    try {
      const payload = {
        url: url,
        title: cleanName,
        quality: "original",
        type: "original",
        ext: "auto",
        filename: cleanName
      };

      await fetch(SERVER_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      });
    } catch (error) {
      console.error("Failed to forward download to Mini Download:", error);
    }
  }
});
