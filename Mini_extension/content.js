(() => {
  const SERVER_URL = "http://127.0.0.1:8765/add";
  const BUTTON_CLASS = "mini-download-video-button";
  const MENU_CLASS = "mini-download-menu";
  const TOAST_CLASS = "mini-download-toast";
  const videos = new WeakMap();
  let activeMenu = null;
  let toastTimer = null;
  let lastHref = location.href;

  function titleForPage() {
    const kind = siteKind();
    if (kind === "youtube" || kind === "facebook" || kind === "tiktok") {
      const title = document.title || "";
      const cleanTitle = title.replace(/\s*-\s*YouTube\s*$/i, "").trim();
      if (cleanTitle) return cleanTitle;
    }
    const og = document.querySelector('meta[property="og:title"], meta[name="twitter:title"]');
    const title = (og && og.content) || document.title || "Mini Download";
    return title.replace(/\s*-\s*YouTube\s*$/i, "").trim() || "Mini Download";
  }

  function titleForVideo(video) {
    if (!video) return titleForPage();
    const kind = siteKind();
    const resolver = siteResolver(kind);
    if (resolver && typeof resolver.titleForVideo === "function") {
      return resolver.titleForVideo(video, titleForPage);
    }
    if (kind === "youtube" && isYoutubeMainVideo(video)) return titleForPage();

    if (kind === "tiktok") {
      let node = video;
      for (let depth = 0; node && depth < 12; depth += 1) {
        const descNode = node.querySelector('[data-e2e="video-desc"], [data-e2e="browse-video-desc"], [class*="VideoDesc"], [class*="DivVideoDesc"]');
        if (descNode && descNode.textContent) {
          const clean = descNode.textContent.replace(/\s+/g, " ").trim();
          if (clean && clean.length > 2) return clean.slice(0, 180);
        }
        node = node.parentElement;
      }
      const url = canonicalUrl(video);
      if (url) {
        const match = url.match(/@([^/]+)\/video\/(\d+)/);
        if (match) return `TikTok ${match[1]} - ${match[2]}`;
      }
    }

    const selectors = 'a[href*="/watch"], a[href*="youtu.be/"], a[href*="/shorts/"], a[href*="/video/"], a[href*="/reel/"], a[href*="/videos/"], a[href*="fb.watch"]';
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
    return titleForPage();
  }

  function siteKind() {
    const host = location.hostname.toLowerCase();
    if (host.includes("youtube.com") || host.includes("youtu.be")) return "youtube";
    if (host.includes("tiktok.com")) return "tiktok";
    if (host.includes("facebook.com") || host.includes("fb.watch")) return "facebook";
    return "other";
  }

  function siteResolver(kind = siteKind()) {
    return window.MiniDownloadSites && window.MiniDownloadSites[kind];
  }

  function canonicalUrl(video) {
    const kind = siteKind();
    const resolver = siteResolver(kind);
    if (resolver && typeof resolver.resolve === "function") {
      return resolver.resolve(video) || "";
    }
    try {
      const url = new URL(location.href);
      if (kind === "youtube") {
        const current = youtubeCurrentPageUrl();
        if (isYoutubeMainVideo(video) && current) return current;
        const nearby = youtubeVideoUrlNear(video, false);
        if (nearby) return nearby;
        if (current) return current;
        const nearest = youtubeVideoUrlNear(video, true);
        if (nearest) return nearest;
        return "";
      }
      if (kind === "tiktok") {
        const nearby = tiktokVideoUrlNear(video);
        if (nearby) return nearby;
        const current = tiktokVideoUrlFromHref(url.href);
        if (current) return current;
        const meta = tiktokVideoUrlFromMetadata();
        if (meta) return meta;
        return "";
      }
      if (kind === "facebook") {
        const nearby = facebookVideoUrlNear(video, false);
        if (nearby) return nearby;
        const manyVideos = visibleVideoCount() > 1;
        const current = facebookVideoUrlFromHref(url.href);
        if (current && !manyVideos) return current;
        const nearest = facebookVideoUrlNear(video, true);
        if (nearest) return nearest;
        const meta = facebookVideoUrlFromMetadata();
        if (meta && !manyVideos) return meta;
        return "";
      }
      if (kind === "other") {
        const media = mediaUrlForOtherSite(video);
        if (media) return media;
        return "";
      }
      url.hash = "";
      return url.href;
    } catch (_) {
      return "";
    }
  }

  function youtubeVideoUrlFromHref(href) {
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

  function youtubeCurrentPageUrl() {
    const current = youtubeVideoUrlFromHref(location.href);
    if (current) return current;
    const nodes = document.querySelectorAll(
      'link[rel="canonical"], meta[property="og:url"], meta[name="twitter:url"]'
    );
    for (const node of nodes) {
      const found = youtubeVideoUrlFromHref(node.href || node.content || "");
      if (found) return found;
    }
    return "";
  }

  function isYoutubeMainVideo(video) {
    if (!video) return false;
    const main = document.querySelector("#movie_player video.html5-main-video, #movie_player video");
    if (main && main === video) return true;
    if (video.closest && video.closest("ytd-watch-flexy")) return true;
    return Boolean(video.classList && video.classList.contains("html5-main-video"));
  }

  function youtubeVideoUrlNear(video, includeGlobalSearch = true) {
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
      const found = youtubeVideoUrlFromHref(anchor.href || anchor.getAttribute("href") || "");
      if (found) return found;
    }
    if (!includeGlobalSearch) return "";

    const videoRect = video.getBoundingClientRect();
    let best = null;
    let bestScore = Number.POSITIVE_INFINITY;
    document.querySelectorAll(selectors).forEach(anchor => {
      const found = youtubeVideoUrlFromHref(anchor.href || anchor.getAttribute("href") || "");
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

  function tiktokVideoUrlFromHref(href) {
    try {
      const url = new URL(href, location.href);
      const match = url.href.match(/https?:\/\/(?:www\.)?tiktok\.com\/@[^/?#]+\/video\/\d+/i);
      return match ? match[0] : "";
    } catch (_) {
      return "";
    }
  }

  function tiktokVideoUrlFromMetadata() {
    const nodes = document.querySelectorAll(
      'link[rel="canonical"], meta[property="og:url"], meta[name="twitter:url"]'
    );
    for (const node of nodes) {
      const found = tiktokVideoUrlFromHref(node.href || node.content || "");
      if (found) return found;
    }
    return "";
  }

  function tiktokVideoUrlNear(video) {
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
      const found = tiktokVideoUrlFromHref(anchor.href || anchor.getAttribute("href") || "");
      if (found) return found;
    }

    const videoRect = video.getBoundingClientRect();
    let best = null;
    let bestScore = Number.POSITIVE_INFINITY;
    document.querySelectorAll('a[href*="/video/"]').forEach(anchor => {
      const found = tiktokVideoUrlFromHref(anchor.href || anchor.getAttribute("href") || "");
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
    const inlineMatch = sourceText.match(/https?:\/\/(?:www\.)?tiktok\.com\/@[^"'<>?\s]+\/video\/\d+/i);
    if (inlineMatch) {
      return tiktokVideoUrlFromHref(inlineMatch[0]);
    }
    return "";
  }

  function facebookVideoUrlFromHref(href) {
    try {
      const url = new URL(href, location.href);
      const clean = `${url.origin}${url.pathname}${url.search}`;
      if (/https?:\/\/(?:web\.|www\.|m\.)?facebook\.com\/reel\/\d+/i.test(clean)) {
        return clean.match(/https?:\/\/(?:web\.|www\.|m\.)?facebook\.com\/reel\/\d+/i)[0];
      }
      const watchId = url.searchParams.get("v");
      if (/\/watch\/?$/i.test(url.pathname) && watchId) {
        return `https://www.facebook.com/watch/?v=${encodeURIComponent(watchId)}`;
      }
      const videoMatch = clean.match(/https?:\/\/(?:web\.|www\.|m\.)?facebook\.com\/[^?#]+\/videos\/\d+/i);
      if (videoMatch) return videoMatch[0];
      const shortMatch = clean.match(/https?:\/\/fb\.watch\/[^/?#]+/i);
      if (shortMatch) return shortMatch[0];
    } catch (_) {}
    return "";
  }

  function facebookVideoUrlFromMetadata() {
    const nodes = document.querySelectorAll(
      'link[rel="canonical"], meta[property="og:url"], meta[name="twitter:url"]'
    );
    for (const node of nodes) {
      const found = facebookVideoUrlFromHref(node.href || node.content || "");
      if (found) return found;
    }
    return "";
  }

  function facebookIdFromUrl(href) {
    try {
      const url = new URL(href, location.href);
      const reelMatch = url.pathname.match(/\/reel\/(\d+)/i);
      if (reelMatch) return `facebook-reel-${reelMatch[1]}`;
      const watchId = url.searchParams.get("v");
      if (watchId) return `facebook-video-${watchId}`;
      const videoMatch = url.pathname.match(/\/videos\/(\d+)/i);
      if (videoMatch) return `facebook-video-${videoMatch[1]}`;
    } catch (_) {}
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

  function filenameForChoice(title, url) {
    if (siteKind() === "facebook" && (!title || /^facebook$/i.test(title.trim()))) {
      const resolver = siteResolver("facebook");
      if (resolver && typeof resolver.idFromUrl === "function") {
        return resolver.idFromUrl(url) || "facebook-video";
      }
      return facebookIdFromUrl(url) || "facebook-video";
    }
    return title || "Mini Download";
  }

  function facebookVideoUrlNear(video, includeGlobalSearch = true) {
    if (!video) return "";
    const selectors = 'a[href*="/reel/"], a[href*="/watch"], a[href*="/videos/"], a[href*="fb.watch"]';
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

    const videoRect = video.getBoundingClientRect();
    const scoredAnchors = anchors => {
      let best = null;
      let bestScore = Number.POSITIVE_INFINITY;
      anchors.forEach(anchor => {
        const found = facebookVideoUrlFromHref(anchor.href || anchor.getAttribute("href") || "");
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
    };

    const scoped = scoredAnchors(scopedAnchors);
    if (scoped.best) return scoped.best;
    if (!includeGlobalSearch) return "";

    let best = null;
    let bestScore = Number.POSITIVE_INFINITY;
    document.querySelectorAll(selectors).forEach(anchor => {
      const found = facebookVideoUrlFromHref(anchor.href || anchor.getAttribute("href") || "");
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

    const sourceText = [
      video.currentSrc,
      video.src,
      video.poster,
      video.outerHTML,
      video.parentElement ? video.parentElement.outerHTML : ""
    ].join(" ");
    const inlineMatch = sourceText.match(/https?:\/\/(?:(?:web|www|m)\.)?facebook\.com\/(?:reel\/\d+|watch\/?\?v=\d+|[^"'<>?\s]+\/videos\/\d+)|https?:\/\/fb\.watch\/[^"'<>?\s]+/i);
    if (inlineMatch) {
      return facebookVideoUrlFromHref(inlineMatch[0]);
    }
    return "";
  }

  function canShowForVideo(video) {
    const kind = siteKind();
    if (kind === "youtube") return Boolean(canonicalUrl(video));
    if (kind === "facebook") return Boolean(canonicalUrl(video));
    if (kind === "tiktok") return true;
    if (kind !== "tiktok" && kind !== "facebook" && kind !== "other") return true;
    return Boolean(canonicalUrl(video));
  }

  function isFacebookActiveVideo(video) {
    if (!video) return false;
    return !video.paused && !video.ended;
  }

  function isMediaUrl(value) {
    const text = normalizeUrlText(value);
    if (!/^https?:\/\//i.test(text)) return false;
    return /\.(m3u8|mpd|mp4|webm|m4v|mov|ts)(?:[?#]|$)/i.test(text) ||
      /(?:mime=video|video\/|application\/x-mpegurl|mpegurl|dash|hls|playlist)/i.test(text);
  }

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

  function bestMediaCandidate(candidates) {
    const unique = [...new Set(candidates.map(absolutizeUrl).filter(Boolean))];
    const ranked = unique.filter(isMediaUrl).sort((a, b) => mediaRank(b) - mediaRank(a));
    return ranked[0] || "";
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

  function mediaUrlForOtherSite(video) {
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

  function parseYoutubePlayerResponse() {
    if (window.ytInitialPlayerResponse && typeof window.ytInitialPlayerResponse === "object") {
      return window.ytInitialPlayerResponse;
    }
    if (window.ytplayer && window.ytplayer.config && window.ytplayer.config.args && window.ytplayer.config.args.player_response) {
      try {
        return JSON.parse(window.ytplayer.config.args.player_response);
      } catch (_) {}
    }
    const scripts = document.querySelectorAll("script");
    for (const script of scripts) {
      if (script.textContent.includes("ytInitialPlayerResponse")) {
        const match = script.textContent.match(/ytInitialPlayerResponse\s*=\s*(\{.*?\});/s);
        if (match) {
          try {
            return JSON.parse(match[1]);
          } catch (_) {}
        }
      }
    }
    return null;
  }

  function availableYoutubeQualities() {
    const response = parseYoutubePlayerResponse();
    if (!response || !response.streamingData) return null;
    const qualities = new Set();
    const formats = [...(response.streamingData.formats || []), ...(response.streamingData.adaptiveFormats || [])];
    for (const format of formats) {
      const label = String(format.qualityLabel || format.quality || "").trim().toLowerCase();
      const match = label.match(/(\d+)p/);
      if (match) {
        qualities.add(Number(match[1]));
        continue;
      }
      if (/highres/.test(label)) {
        qualities.add(2160);
        continue;
      }
      if (/4k|2160/.test(label)) {
        qualities.add(2160);
        continue;
      }
      if (/1440|2k/.test(label)) {
        qualities.add(1440);
        continue;
      }
    }
    if (qualities.size === 0) return null;
    return qualities;
  }

  function getMaxAvailableQuality() {
    const available = availableYoutubeQualities();
    if (!available || available.size === 0) return null;
    return Math.max(...Array.from(available));
  }

  function formatChoices() {
    const kind = siteKind();
    if (kind === "youtube") {
      const maxQuality = getMaxAvailableQuality();
      const choices = [
        { label: "4K MP4", quality: "2160", type: "mp4", ext: "mp4", format_label: "MP4 with size 4K" },
        { label: "1440P MP4", quality: "1440", type: "mp4", ext: "mp4", format_label: "MP4 with size 1440P" },
        { label: "1080P MP4", quality: "1080", type: "mp4", ext: "mp4", format_label: "MP4 with size 1080P" },
        { label: "720P MP4", quality: "720", type: "mp4", ext: "mp4", format_label: "MP4 with size 720P" },
        { label: "Original", quality: "original", type: "original", ext: "auto", format_label: "Original" },
        { label: "MP3 128kb", quality: "audio_128", type: "mp3", ext: "mp3", audio_bitrate: "128K", format_label: "MP3 128kb" },
        { label: "MP3 256kb", quality: "audio_256", type: "mp3", ext: "mp3", audio_bitrate: "256K", format_label: "MP3 256kb" }
      ];
      if (maxQuality === null) return choices;
      return choices.filter(choice => {
        if (choice.type === "mp3" || choice.quality === "original") return true;
        const qualityNumber = Number(choice.quality);
        return !Number.isNaN(qualityNumber) && qualityNumber <= maxQuality;
      });
    }
    if (kind === "tiktok" || kind === "facebook") {
      return [
        { label: "1080P MP4", quality: "1080", type: "mp4", ext: "mp4", format_label: "MP4 with size 1080P" },
        { label: "720P MP4", quality: "720", type: "mp4", ext: "mp4", format_label: "MP4 with size 720P" },
        { label: "Original", quality: "original", type: "original", ext: "auto", format_label: "Original" }
      ];
    }
    return [
      { label: "Original", quality: "original", type: "original", ext: "auto", format_label: "Original" },
      { label: "1080P MP4", quality: "1080", type: "mp4", ext: "mp4", format_label: "MP4 with size 1080P" },
      { label: "720P MP4", quality: "720", type: "mp4", ext: "mp4", format_label: "MP4 with size 720P" },
      { label: "MP3 128kb", quality: "audio_128", type: "mp3", ext: "mp3", audio_bitrate: "128K", format_label: "MP3 128kb" },
      { label: "MP3 256kb", quality: "audio_256", type: "mp3", ext: "mp3", audio_bitrate: "256K", format_label: "MP3 256kb" }
    ];
  }

  function payloadFor(choice, video) {
    const title = titleForVideo(video);
    const state = videos.get(video);
    const resolvedUrl = canonicalUrl(video);
    const filename = filenameForChoice(title, resolvedUrl);
    if (state) state.url = resolvedUrl;
    return {
      url: resolvedUrl,
      title,
      cookie_site: siteKind(),
      quality: choice.quality,
      type: choice.type,
      ext: choice.ext,
      audio_bitrate: choice.audio_bitrate || "",
      format_label: choice.format_label,
      filename
    };
  }

  function positionButton(video, button) {
    const rect = video.getBoundingClientRect();
    if (rect.width < 120 || rect.height < 80 || !canShowForVideo(video)) {
      button.classList.remove("mini-download-visible");
      button.classList.remove("mini-download-dimmed");
      return;
    }
    button.style.top = `${Math.max(8, window.scrollY + rect.top + 10)}px`;
    button.style.left = `${Math.max(8, window.scrollX + rect.left + 10)}px`;
  }

  async function sendItem(item, button) {
    if (!item.url) {
      const label = button.querySelector('.mini-download-button-label');
      if (label) label.textContent = "No video URL";
      button.classList.add("mini-download-error");
      showToast("Mini Download could not find a video URL for this item.");
      setTimeout(() => {
        const label = button.querySelector('.mini-download-button-label');
        if (label) label.textContent = "Mini Download";
        button.classList.remove("mini-download-error");
      }, 2200);
      return;
    }
    {
      const label = button.querySelector('.mini-download-button-label');
      if (label) label.textContent = "Sending";
    }
    button.classList.remove("mini-download-error");
    try {
      const response = await fetch(SERVER_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(item)
      });
      if (!response.ok) {
        let error = "";
        try {
          error = (await response.json()).error || "";
        } catch (_) {}
        throw new Error(error || `Mini Download returned ${response.status}`);
      }
      {
        const label = button.querySelector('.mini-download-button-label');
        if (label) label.textContent = "Added";
      }
      button.classList.add("mini-download-sent");
      setTimeout(() => {
        const label = button.querySelector('.mini-download-button-label');
        if (label) label.textContent = "Mini Download";
        button.classList.remove("mini-download-sent");
      }, 1200);
    } catch (error) {
      {
        const label = button.querySelector('.mini-download-button-label');
        if (label) label.textContent = "Open Mini Download";
      }
      button.classList.add("mini-download-error");
      const message = String(error && error.message || "");
      if (message === "tiktok_video_url_required") {
        showToast("Mini Download needs the actual TikTok video URL. Open the video page, then try again.");
      } else if (message === "facebook_video_url_required") {
        showToast("Mini Download could not find the Facebook reel/watch URL for this video.");
      } else if (message === "invalid_url" || message.startsWith("Mini Download returned")) {
        showToast("Mini Download could not use this video URL. Try Original or open the video page directly.");
      } else {
        showToast("Mini Download app is not running. Please open Mini Download 5.5 or newer, then try again.");
      }
      setTimeout(() => {
        const label = button.querySelector('.mini-download-button-label');
        if (label) label.textContent = "Mini Download";
        button.classList.remove("mini-download-error");
      }, 1800);
    }
  }

  function showToast(message) {
    let toast = document.querySelector(`.${TOAST_CLASS}`);
    if (!toast) {
      toast = document.createElement("div");
      toast.className = TOAST_CLASS;
      document.documentElement.appendChild(toast);
    }
    toast.textContent = message;
    toast.classList.add("mini-download-toast-visible");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      toast.classList.remove("mini-download-toast-visible");
    }, 4200);
  }

  function closeMenu() {
    if (activeMenu) {
      activeMenu.remove();
      activeMenu = null;
    }
  }

  function showMenu(video, button) {
    if (!canShowForVideo(video)) {
      button.classList.remove("mini-download-visible");
      button.classList.remove("mini-download-dimmed");
      return;
    }
    closeMenu();
    const menu = document.createElement("div");
    menu.className = MENU_CLASS;
    const rect = button.getBoundingClientRect();
    const menuWidth = Math.min(480, window.innerWidth - 16);
    menu.style.top = `${window.scrollY + rect.bottom + 4}px`;
    menu.style.left = `${Math.max(8, Math.min(window.scrollX + rect.left, window.scrollX + window.innerWidth - menuWidth - 8))}px`;
    menu.innerHTML = `
      <div class="mini-download-menu-title"><span>▶</span> Mini Download - Select quality <button type="button" aria-label="Hide list" title="Hide list">×</button></div>
      <div class="mini-download-menu-list"></div>
      <div class="mini-download-menu-note">Supports Mini Download 5.5 or newer. All rights reserved by Admin-Kh.</div>
    `;
    const list = menu.querySelector(".mini-download-menu-list");
    const videoTitle = titleForVideo(video);
    formatChoices().forEach((choice, index) => {
      const row = document.createElement("button");
      row.type = "button";
      const icon = choice.type === "mp3" ? "🎵" : "🎬";
      const rowIcon = document.createElement("span");
      rowIcon.className = "mini-download-row-icon";
      rowIcon.textContent = icon;
      const rowText = document.createElement("span");
      rowText.className = "mini-download-row-text";
      const qualityText = document.createElement("span");
      qualityText.className = "mini-download-row-quality";
      qualityText.textContent = choice.label;
      const titleText = document.createElement("span");
      titleText.className = "mini-download-row-title";
      titleText.textContent = ` - ${videoTitle}`;
      rowText.appendChild(qualityText);
      rowText.appendChild(titleText);
      row.appendChild(rowIcon);
      row.appendChild(rowText);
      row.addEventListener("click", event => {
        event.preventDefault();
        event.stopPropagation();
        closeMenu();
        sendItem(payloadFor(choice, video), button);
      });
      list.appendChild(row);
    });
    menu.querySelector(".mini-download-menu-title button").addEventListener("click", event => {
      event.preventDefault();
      event.stopPropagation();
      closeMenu();
    });
    document.documentElement.appendChild(menu);
    activeMenu = menu;
  }

  function attach(video) {
    if (videos.has(video)) return;
    const kind = siteKind();
    if (kind !== "facebook" && !canShowForVideo(video)) return;
    if (kind === "facebook") {
      const rect = video.getBoundingClientRect();
      if (rect.width < 120 || rect.height < 80) return;
    }
    const button = document.createElement("button");
    button.type = "button";
    button.className = BUTTON_CLASS;
    button.innerHTML = `
      <span class="mini-download-button-label">Mini Download</span>
      <span class="mini-download-button-refresh" title="Refresh video state">⟳</span>
    `;
    button.title = "Mini Download";
    document.documentElement.appendChild(button);
    button.videoElement = video;

    const refreshIcon = button.querySelector(".mini-download-button-refresh");
    if (refreshIcon) {
      const refreshHandler = event => {
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        // Force reload the page to restart the extension's scanning process
        showToast("Reloading...");
        setTimeout(() => location.reload(), 300);
      };

      refreshIcon.addEventListener("mousedown", event => {
        event.stopPropagation();
      });
      refreshIcon.addEventListener("click", refreshHandler);
    }

    const show = () => {
      if (!refreshVideoState(video)) return;
      button.classList.add("mini-download-visible");
      button.classList.remove("mini-download-dimmed");
    };
    const hide = () => {
      setTimeout(() => {
        if (!button.matches(":hover") && !(activeMenu && activeMenu.matches(":hover"))) {
          button.classList.add("mini-download-dimmed");
        }
      }, 350);
    };
    const hideNow = () => {
      if (siteKind() !== "facebook") {
        button.classList.remove("mini-download-visible");
        button.classList.remove("mini-download-dimmed");
        closeMenu();
      }
    };
    const update = () => refreshVideoState(video);

    button.addEventListener("click", event => {
      event.preventDefault();
      event.stopPropagation();
      showMenu(video, button);
    });

    let hoverTarget = video;
    if (video.parentElement && video.parentElement.tagName !== "BODY" && video.parentElement.tagName !== "HTML") {
      hoverTarget = video.parentElement;
    }

    button.addEventListener("mouseenter", show);
    button.addEventListener("mouseleave", hide);
    hoverTarget.addEventListener("mouseenter", show);
    hoverTarget.addEventListener("mousemove", show);
    video.addEventListener("loadedmetadata", show);
    video.addEventListener("play", show);
    video.addEventListener("playing", show);
    video.addEventListener("timeupdate", update);
    video.addEventListener("pause", hideNow);
    video.addEventListener("ended", hideNow);
    hoverTarget.addEventListener("mouseleave", hide);
    window.addEventListener("scroll", update, true);
    window.addEventListener("resize", update);
    const initialUrl = canonicalUrl(video);
    videos.set(video, {
      button,
      update,
      url: initialUrl,
      src: video.currentSrc || video.src || "",
      waitingForUrl: !initialUrl
    });
  }

  function refreshVideoState(video) {
    const state = videos.get(video);
    if (!state) return false;
    const url = canonicalUrl(video);
    const src = video.currentSrc || video.src || "";
    const kind = siteKind();
    const requiresUrl = kind !== "tiktok";
    if ((requiresUrl && !url) || video.getBoundingClientRect().width < 120 || video.getBoundingClientRect().height < 80) {
      state.button.classList.remove("mini-download-visible");
      state.button.classList.remove("mini-download-dimmed");
      state.url = "";
      state.src = src;
      state.waitingForUrl = true;
      closeMenu();
      return false;
    }
    state.url = url;
    state.src = src;
    state.waitingForUrl = !url;
    positionButton(video, state.button);
    return true;
  }

  function retryMissingUrls() {
    document.querySelectorAll("video").forEach(video => {
      if (!videos.has(video)) {
        attach(video);
        return;
      }
      const state = videos.get(video);
      if (!state) return;
      const kind = siteKind();
      const shouldRetry = state.waitingForUrl || kind === "facebook";
      if (!shouldRetry) return;
      if (refreshVideoState(video)) {
        state.button.classList.add("mini-download-visible");
        state.button.classList.remove("mini-download-dimmed");
      }
    });
  }

  function scan() {
    document.querySelectorAll("." + BUTTON_CLASS).forEach(button => {
      const video = button.videoElement;
      if (!video || !video.isConnected) {
        button.remove();
      }
    });

    document.querySelectorAll("video").forEach(video => {
      if (videos.has(video)) {
        refreshVideoState(video);
      } else {
        attach(video);
      }
    });
  }

  document.addEventListener("click", event => {
    if (activeMenu && !activeMenu.contains(event.target) && !event.target.classList.contains(BUTTON_CLASS)) closeMenu();
  }, true);

  const observer = new MutationObserver(scan);
  observer.observe(document.documentElement, { childList: true, subtree: true });

  function refreshOnUrlChange() {
    if (location.href === lastHref) return;
    lastHref = location.href;
    scan();
  }

  const originalPushState = history.pushState;
  history.pushState = function (...args) {
    const result = originalPushState.apply(this, args);
    refreshOnUrlChange();
    return result;
  };

  const originalReplaceState = history.replaceState;
  history.replaceState = function (...args) {
    const result = originalReplaceState.apply(this, args);
    refreshOnUrlChange();
    return result;
  };

  window.addEventListener("popstate", refreshOnUrlChange);
  setInterval(refreshOnUrlChange, 500);
  scan();
  setInterval(scan, 1000);
  setInterval(retryMissingUrls, 1000);
})();
