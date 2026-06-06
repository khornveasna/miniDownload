(() => {
  window.MiniDownloadSites = window.MiniDownloadSites || {};

  const selectors = 'a[href*="/reel/"], a[href*="/watch"], a[href*="/videos/"], a[href*="fb.watch"]';

  function urlFromHref(href) {
    try {
      const url = new URL(href, location.href);
      const clean = `${url.origin}${url.pathname}${url.search}`;
      const reel = clean.match(/https?:\/\/(?:web\.|www\.|m\.)?facebook\.com\/reel\/\d+/i);
      if (reel) return reel[0];
      const watchId = url.searchParams.get("v");
      if (/\/watch\/?$/i.test(url.pathname) && watchId) {
        return `https://www.facebook.com/watch/?v=${encodeURIComponent(watchId)}`;
      }
      const video = clean.match(/https?:\/\/(?:web\.|www\.|m\.)?facebook\.com\/[^?#]+\/videos\/\d+/i);
      if (video) return video[0];
      const short = clean.match(/https?:\/\/fb\.watch\/[^/?#]+/i);
      if (short) return short[0];
    } catch (_) {}
    return "";
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

  function visibleVideoCount() {
    let count = 0;
    document.querySelectorAll("video").forEach(video => {
      const rect = video.getBoundingClientRect();
      if (rect.width >= 120 && rect.height >= 80 && rect.bottom > 0 && rect.right > 0 &&
          rect.top < window.innerHeight && rect.left < window.innerWidth) {
        count += 1;
      }
    });
    return count;
  }

  function scoreAnchors(video, anchors) {
    const videoRect = video.getBoundingClientRect();
    let best = null;
    let bestScore = Number.POSITIVE_INFINITY;
    anchors.forEach(anchor => {
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
    return {best, bestScore};
  }

  function near(video, includeGlobalSearch = true) {
    if (!video) return "";
    const scopedAnchors = [];
    const seen = new Set();
    let node = video;
    for (let depth = 0; node && depth < 10; depth += 1) {
      if (node.matches && node.matches(selectors) && !seen.has(node)) {
        seen.add(node);
        scopedAnchors.push(node);
      }
      if (node.querySelectorAll) {
        node.querySelectorAll(selectors).forEach(anchor => {
          if (!seen.has(anchor)) {
            seen.add(anchor);
            scopedAnchors.push(anchor);
          }
        });
      }
      node = node.parentElement;
    }

    const scoped = scoreAnchors(video, scopedAnchors);
    if (scoped.best) return scoped.best;
    if (!includeGlobalSearch) return "";

    const global = scoreAnchors(video, [...document.querySelectorAll(selectors)]);
    const rect = video.getBoundingClientRect();
    if (global.best && global.bestScore < Math.max(620, rect.width + rect.height)) return global.best;

    const sourceText = [
      video.currentSrc,
      video.src,
      video.poster,
      video.outerHTML,
      video.parentElement ? video.parentElement.outerHTML : ""
    ].join(" ");
    const inline = sourceText.match(/https?:\/\/(?:(?:web|www|m)\.)?facebook\.com\/(?:reel\/\d+|watch\/?\?v=\d+|[^"'<>?\s]+\/videos\/\d+)|https?:\/\/fb\.watch\/[^"'<>?\s]+/i);
    return inline ? urlFromHref(inline[0]) : "";
  }

  function resolve(video) {
    const scoped = near(video, false);
    if (scoped) return scoped;
    const current = urlFromHref(location.href);
    if (current && visibleVideoCount() <= 1) return current;
    const global = near(video, true);
    if (global) return global;
    const meta = metadataUrl();
    return visibleVideoCount() <= 1 ? meta : "";
  }

  function idFromUrl(href) {
    try {
      const url = new URL(href, location.href);
      const reel = url.pathname.match(/\/reel\/(\d+)/i);
      if (reel) return `facebook-reel-${reel[1]}`;
      const watchId = url.searchParams.get("v");
      if (watchId) return `facebook-video-${watchId}`;
      const video = url.pathname.match(/\/videos\/(\d+)/i);
      if (video) return `facebook-video-${video[1]}`;
    } catch (_) {}
    return "";
  }

  window.MiniDownloadSites.facebook = {resolve, idFromUrl};
})();
