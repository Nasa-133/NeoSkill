'use client';

import { useEffect, useState } from 'react';

/**
 * Turns whatever an admin pasted into a playable source.
 *
 * Supported: YouTube, Cloudflare Stream, Vimeo and direct media files. Anything else
 * falls back to a link, so a lesson never shows a silently broken player.
 */

export function youtubeId(url: string): string | null {
  try {
    const parsed = new URL(url.trim());
    const host = parsed.hostname.replace(/^www\./, '');
    if (host === 'youtu.be') return parsed.pathname.slice(1).split('/')[0] || null;
    if (host !== 'youtube.com' && host !== 'm.youtube.com' && host !== 'youtube-nocookie.com') return null;
    if (parsed.pathname === '/watch') return parsed.searchParams.get('v');
    const match = /^\/(embed|shorts|live|v)\/([^/?]+)/.exec(parsed.pathname);
    return match?.[2] ?? null;
  } catch { return null; }
}

/**
 * Cloudflare Stream embed URL, or null when this is not a Stream link.
 *
 * A signed URL carries its token in the first path segment instead of the video id,
 * so an already-correct /iframe URL is passed through untouched — rebuilding it
 * would drop the token and break playback.
 */
export function cloudflareStreamEmbed(url: string): string | null {
  try {
    const parsed = new URL(url.trim());
    const host = parsed.hostname.replace(/^www\./, '');
    const isStream =
      host.endsWith('.cloudflarestream.com') ||
      host === 'cloudflarestream.com' ||
      host === 'videodelivery.net' ||
      host === 'iframe.videodelivery.net';
    if (!isStream) return null;

    const segments = parsed.pathname.split('/').filter(Boolean);
    if (segments.length === 0) return null;
    if (segments[segments.length - 1] === 'iframe') return parsed.toString();

    // /<id>/watch, /<id>/manifest/video.m3u8, /<id>/thumbnails/... and bare /<id>
    const id = segments[0];
    if (!id) return null;
    const base = host === 'iframe.videodelivery.net' ? 'https://iframe.videodelivery.net' : `${parsed.origin}`;
    const path = host === 'iframe.videodelivery.net' ? `/${id}` : `/${id}/iframe`;
    return `${base}${path}${parsed.search}`;
  } catch { return null; }
}

export function vimeoEmbed(url: string): string | null {
  try {
    const parsed = new URL(url.trim());
    const host = parsed.hostname.replace(/^www\./, '');
    if (host === 'player.vimeo.com') return parsed.toString();
    if (host !== 'vimeo.com') return null;
    const id = parsed.pathname.split('/').filter(Boolean)[0];
    return /^\d+$/.test(id ?? '') ? `https://player.vimeo.com/video/${id}` : null;
  } catch { return null; }
}

/**
 * Hosts whose player URLs are embedded as given.
 *
 * These are the DRM-capable providers (Widevine / FairPlay) a paid course would move
 * to, so pasting their embed link is enough — no code change per provider.
 */
const EMBED_HOSTS = new Set([
  'kinescope.io',
  'player.vdocipher.com',
  'iframe.mediadelivery.net',
  'play.gumlet.io',
]);

export function knownEmbedHost(url: string): string | null {
  try {
    const parsed = new URL(url.trim());
    const host = parsed.hostname.replace(/^www\./, '');
    if (host !== 'kinescope.io') return EMBED_HOSTS.has(host) ? parsed.toString() : null;
    // kinescope.io/<id> watch links need the /embed/ prefix before they render.
    const segments = parsed.pathname.split('/').filter(Boolean);
    if (segments[0] === 'embed') return parsed.toString();
    return segments[0] ? `https://kinescope.io/embed/${segments[0]}${parsed.search}` : null;
  } catch { return null; }
}

const fileExtension = /\.(mp4|webm|ogg|ogv|m4v)(\?.*)?$/i;

/** The embed URL for a lesson video, or null when it can only be opened in a new tab. */
export function embedSource(url: string): string | null {
  const trimmed = url.trim();
  if (!trimmed) return null;
  const youtube = youtubeId(trimmed);
  if (youtube) return `https://www.youtube-nocookie.com/embed/${encodeURIComponent(youtube)}?rel=0&modestbranding=1`;
  return cloudflareStreamEmbed(trimmed) ?? vimeoEmbed(trimmed) ?? knownEmbedHost(trimmed);
}

/** Six resting spots, so the mark cannot be cropped away by trimming one edge. */
const SPOTS = [
  { top: '8%', left: '6%' },
  { top: '8%', right: '6%' },
  { bottom: '18%', left: '6%' },
  { bottom: '18%', right: '6%' },
  { top: '46%', left: '30%' },
  { top: '30%', right: '24%' },
] as const;

const MOVE_EVERY_MS = 18_000;

/**
 * Per-viewer mark burned into anything captured from the screen.
 *
 * This does not stop a recording — nothing in a browser can. It ties any copy that
 * leaks back to the account it came from, which is what actually deters sharing.
 * A determined viewer can strip it in devtools; a casual one records it along with
 * the video.
 */
export function VideoWatermark({ label }: { label: string }) {
  const [spot, setSpot] = useState(0);
  const [stamp, setStamp] = useState('');

  useEffect(() => {
    const tick = () => {
      setSpot(value => (value + 1) % SPOTS.length);
      setStamp(new Date().toLocaleString('uz-UZ', { dateStyle: 'short', timeStyle: 'short' }));
    };
    tick();
    const timer = window.setInterval(tick, MOVE_EVERY_MS);
    return () => window.clearInterval(timer);
  }, []);

  return <span className="ns-video-mark" style={SPOTS[spot]} aria-hidden="true">
    {label}{stamp ? ` · ${stamp}` : ''}
  </span>;
}

export function VideoPlayer({ url, title, watermark }: { url: string; title: string; watermark?: string }) {
  const trimmed = url.trim();
  if (!trimmed) return <div className="ns-video"><p>Bu darsga hali video biriktirilmagan.</p></div>;

  const mark = watermark ? <VideoWatermark label={watermark} /> : null;
  const embed = embedSource(trimmed);
  if (embed) return <div className="ns-video ns-video--embed">
    <iframe
      src={embed}
      title={title}
      loading="lazy"
      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share; fullscreen"
      allowFullScreen
    />
    {mark}
  </div>;

  if (fileExtension.test(trimmed)) return <div className="ns-video ns-video--embed">
    {/* Downloads are pointless here: the file itself is what we are protecting. */}
    <video src={trimmed} controls preload="metadata" playsInline disablePictureInPicture controlsList="nodownload" />
    {mark}
  </div>;

  return <div className="ns-video">
    <p>Bu video havolasini sahifa ichida ko‘rsatib bo‘lmaydi.</p>
    <a className="ns-link-button ns-link-button--secondary" href={trimmed} target="_blank" rel="noreferrer">Videoni yangi oynada ochish ↗</a>
  </div>;
}
