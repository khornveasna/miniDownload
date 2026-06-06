(() => {
  window.MiniDownloadSites = window.MiniDownloadSites || {};

  function normalizeUrlText(value) {
    return String(value || "")
      .replace(/\\u0026/g, "&")
      .replace(/\\\//g, "/")
      .replace(/&amp;/g, "&");
  }

  function absolutizeUrl(value) {
    try {
      const decoded = normalizeUrlText(value);
      if (decoded.startsWith("blob:")) return "";
      return new URL(decoded, location.href).href;
    } catch (_) {
      return "";
    }
  }

  function isMediaUrl(value) {
    const text = normalizeUrlText(value);
    if (!/^https?:\/\//i.test(text)) return false;
    return /\.(m3u8|mpd|mp4|webm|m4v|mov|ts)(?:[?#]|$)/i.test(text) ||
      /(?:mime=video|video\/|application\/x-mpegurl|mpegurl|dash|hls|playlist)/i.test(text);
  }

  function mediaRank(url) {
    if (/\.m3u8(?:[?#]|$)/i.test(url)) return 100;
    if (/\.mpd(?:[?#]|$)/i.test(url)) return 95;
    if (/\.mp4(?:[?#]|$)/i.test(url)) return 80;
    if (/\.webm(?:[?#]|$)/i.test(url)) return 75;
    if (/\.m4v|\.mov/i.test(url)) return 70;
    if (/\.ts(?:[?#]|$)/i.test(url)) return 35;
    return 1;
  }

  function bestMediaCandidate(candidates) {
    const unique = [...new Set(candidates.map(absolutizeUrl).filter(Boolean))];
    const ranked = unique.filter(isMediaUrl).sort((a, b) => mediaRank(b) - mediaRank(a));
    return ranked[0] || "";
  }

  function resolve(video) {
    if (!video) return "";
    const candidates = [
      video.currentSrc,
      video.src,
      video.getAttribute("src"),
      video.poster
    ];
    video.querySelectorAll("source[src]").forEach(source => candidates.push(source.src || source.getAttribute("src")));

    let node = video;
    for (let depth = 0; node && depth < 6; depth += 1) {
      if (node.querySelectorAll) {
        node.querySelectorAll("source[src], a[href], [src], [data-src], [data-url], [data-video], [data-file]").forEach(el => {
          ["src", "href", "data-src", "data-url", "data-video", "data-file"].forEach(attr => candidates.push(el.getAttribute(attr) || ""));
        });
      }
      candidates.push(node.outerHTML || "");
      node = node.parentElement;
    }

    try {
      performance.getEntriesByType("resource").forEach(entry => candidates.push(entry.name || ""));
    } catch (_) {}

    const joined = normalizeUrlText(candidates.join(" "));
    const urlMatches = joined.match(/https?:\/\/[^"'<>\\\s]+(?:m3u8|mpd|mp4|webm|m4v|mov|\.ts)(?:[^"'<>\\\s]*)?/gi) || [];
    candidates.push(...urlMatches);
    return bestMediaCandidate(candidates);
  }

  window.MiniDownloadSites.other = {resolve};
})();
