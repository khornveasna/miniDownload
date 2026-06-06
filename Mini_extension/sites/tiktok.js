(() => {
  window.MiniDownloadSites = window.MiniDownloadSites || {};

  function urlFromHref(href) {
    try {
      const url = new URL(href, location.href);
      const match = url.href.match(/https?:\/\/(?:www\.)?tiktok\.com\/@[^/?#]+\/video\/\d+/i);
      return match ? match[0] : "";
    } catch (_) {
      return "";
    }
  }

  function metadataUrl() {
    const nodes = document.querySelectorAll(
      'link[rel="canonical"], meta[property="og:url"], meta[name="twitter:url"]'
    );
    for (const node of nodes) {
      const found = urlFromHref(node.href || node.content || "");
      if (found) return found;
    }
    return "";
  }

  function near(video) {
    if (!video) return "";
    const seen = new Set();
    const scopedAnchors = [];
    let node = video;
    for (let depth = 0; node && depth < 8; depth += 1) {
      if (node.querySelectorAll) {
        node.querySelectorAll('a[href*="/video/"]').forEach(anchor => {
          if (!seen.has(anchor)) {
            seen.add(anchor);
            scopedAnchors.push(anchor);
          }
        });
      }
      node = node.parentElement;
    }
    for (const anchor of scopedAnchors) {
      const found = urlFromHref(anchor.href || anchor.getAttribute("href") || "");
      if (found) return found;
    }

    const videoRect = video.getBoundingClientRect();
    let best = null;
    let bestScore = Number.POSITIVE_INFINITY;
    document.querySelectorAll('a[href*="/video/"]').forEach(anchor => {
      const found = urlFromHref(anchor.href || anchor.getAttribute("href") || "");
      if (!found) return;
      const rect = anchor.getBoundingClientRect();
      const overlapX = Math.max(0, Math.min(videoRect.right, rect.right) - Math.max(videoRect.left, rect.left));
      const overlapY = Math.max(0, Math.min(videoRect.bottom, rect.bottom) - Math.max(videoRect.top, rect.top));
      const overlapArea = overlapX * overlapY;
      const dx = Math.abs((videoRect.left + videoRect.right) / 2 - (rect.left + rect.right) / 2);
      const dy = Math.abs((videoRect.top + videoRect.bottom) / 2 - (rect.top + rect.bottom) / 2);
      const score = overlapArea > 0 ? -overlapArea : dx + dy;
      if (score < bestScore) {
        bestScore = score;
        best = found;
      }
    });
    if (best && bestScore < Math.max(520, videoRect.width + videoRect.height)) return best;

    const sourceText = [
      video.currentSrc,
      video.src,
      video.poster,
      video.outerHTML,
      video.parentElement ? video.parentElement.outerHTML : ""
    ].join(" ");
    const inline = sourceText.match(/https?:\/\/(?:www\.)?tiktok\.com\/@[^"'<>?\s]+\/video\/\d+/i);
    return inline ? urlFromHref(inline[0]) : "";
  }

  function resolve(video) {
    return near(video) || urlFromHref(location.href) || metadataUrl();
  }

  window.MiniDownloadSites.tiktok = {resolve};
})();
