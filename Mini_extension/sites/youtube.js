(() => {
  window.MiniDownloadSites = window.MiniDownloadSites || {};

  function urlFromHref(href) {
    try {
      const url = new URL(href, location.href);
      const host = url.hostname.toLowerCase();
      if (!host.includes("youtube.com") && !host.includes("youtu.be")) return "";
      let id = url.searchParams.get("v");
      if (!id && host.includes("youtu.be")) id = url.pathname.split("/").filter(Boolean)[0];
      if (!id && url.pathname.includes("/shorts/")) id = url.pathname.split("/shorts/")[1].split(/[/?#]/)[0];
      if (!id && url.pathname.includes("/embed/")) id = url.pathname.split("/embed/")[1].split(/[/?#]/)[0];
      if (!id || !/^[A-Za-z0-9_-]{6,}$/.test(id)) return "";
      return `https://www.youtube.com/watch?v=${encodeURIComponent(id)}`;
    } catch (_) {
      return "";
    }
  }

  function currentPageUrl() {
    const current = urlFromHref(location.href);
    if (current) return current;
    const nodes = document.querySelectorAll(
      'link[rel="canonical"], meta[property="og:url"], meta[name="twitter:url"]'
    );
    for (const node of nodes) {
      const found = urlFromHref(node.href || node.content || "");
      if (found) return found;
    }
    return "";
  }

  function isMainVideo(video) {
    if (!video) return false;
    const main = document.querySelector("#movie_player video.html5-main-video, #movie_player video");
    if (main && main === video) return true;
    if (video.closest && video.closest("ytd-watch-flexy")) return true;
    return Boolean(video.classList && video.classList.contains("html5-main-video"));
  }

  function near(video, includeGlobalSearch = true) {
    if (!video) return "";
    const selectors = 'a[href*="/watch"], a[href*="youtu.be/"], a[href*="/shorts/"], a[href*="/embed/"]';
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
    for (const anchor of scopedAnchors) {
      const found = urlFromHref(anchor.href || anchor.getAttribute("href") || "");
      if (found) return found;
    }
    if (!includeGlobalSearch) return "";

    const videoRect = video.getBoundingClientRect();
    let best = null;
    let bestScore = Number.POSITIVE_INFINITY;
    document.querySelectorAll(selectors).forEach(anchor => {
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
    if (best && bestScore < Math.max(620, videoRect.width + videoRect.height)) return best;
    return "";
  }

  function resolve(video) {
    const current = currentPageUrl();
    if (isMainVideo(video) && current) return current;
    const scoped = near(video, false);
    if (scoped) return scoped;
    if (current) return current;
    return near(video, true);
  }

  function titleForVideo(video, fallback) {
    if (!video || isMainVideo(video)) return fallback();
    const selectors = 'a[href*="/watch"], a[href*="youtu.be/"], a[href*="/shorts/"]';
    let node = video;
    for (let depth = 0; node && depth < 10; depth += 1) {
      const anchors = [];
      if (node.matches && node.matches(selectors)) anchors.push(node);
      if (node.querySelectorAll) anchors.push(...node.querySelectorAll(selectors));
      for (const anchor of anchors) {
        const raw = anchor.getAttribute("aria-label") || anchor.getAttribute("title") || anchor.textContent || "";
        const clean = raw.replace(/\s+/g, " ").replace(/\s*-\s*YouTube\s*$/i, "").trim();
        if (clean && clean.length > 3) return clean.slice(0, 180);
      }
      node = node.parentElement;
    }
    return fallback();
  }

  window.MiniDownloadSites.youtube = {resolve, titleForVideo, isMainVideo};
})();
