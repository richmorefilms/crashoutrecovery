/**
 * Example React modal — Add Crashout Video (Creator).
 * Live app uses the vanilla modal in static/crashout-videos.js; this mirrors that API.
 *
 * Usage:
 *   <AddVideoModal
 *     open={open}
 *     onClose={() => setOpen(false)}
 *     onAdded={(video) => refreshMoments(video)}
 *   />
 */
import React, { useState } from "react";

async function resolveVideo({ query, youtubeId }) {
  const res = await fetch("/api/youtube/resolve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      manual_id: youtubeId || null,
      persist: true,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(typeof err.detail === "string" ? err.detail : `Resolve failed (${res.status})`);
  }
  return res.json();
}

export function AddVideoModal({ open = true, onClose, onAdded }) {
  const [query, setQuery] = useState("");
  const [youtubeId, setYoutubeId] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState(null);

  if (!open) return null;

  const handleSubmit = async (e) => {
    e?.preventDefault?.();
    if (!query.trim()) {
      setStatus("Search query is required.");
      return;
    }
    setBusy(true);
    setStatus("Saving…");
    setPreview(null);
    try {
      const data = await resolveVideo({
        query: query.trim(),
        youtubeId: youtubeId.trim() || null,
      });
      setStatus(`Saved (${data.source}) — ${data.youtubeId}`);
      setPreview(data);
      onAdded?.(data);
      // Brief pause so creators see the toast embed preview, then close
      window.setTimeout(() => onClose?.(), 600);
    } catch (err) {
      setStatus(err.message || "Could not add video");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="video-manual-modal" role="presentation">
      <div className="video-manual-modal-backdrop" onClick={onClose} />
      <div
        className="video-manual-modal-sheet"
        role="dialog"
        aria-modal="true"
        aria-labelledby="add-video-title"
      >
        <header className="video-manual-header">
          <h2 id="add-video-title" className="video-manual-title">
            Add Crashout Video
          </h2>
          <button type="button" className="video-manual-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </header>

        <form className="video-manual-form" onSubmit={handleSubmit}>
          <label className="video-manual-label">
            Search query
            <input
              className="video-manual-input"
              type="text"
              placeholder="Gucci Mane SPEAKS OUT…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              required
              maxLength={500}
            />
          </label>

          <label className="video-manual-label">
            YouTube ID (optional manual override)
            <input
              className="video-manual-input"
              type="text"
              placeholder="m65MJSC1Jto or https://youtu.be/…"
              value={youtubeId}
              onChange={(e) => setYoutubeId(e.target.value)}
              maxLength={200}
            />
          </label>

          {status ? (
            <p className="video-manual-status" role="status">
              {status}
            </p>
          ) : null}

          <div className="video-manual-actions">
            <button type="submit" className="video-manual-submit" disabled={busy}>
              Submit
            </button>
            <button type="button" className="video-manual-cancel" onClick={onClose}>
              Cancel
            </button>
          </div>
        </form>

        {preview?.youtubeId ? (
          <div className="video-manual-preview">
            <div className="crashout-video-frame">
              <iframe
                src={`https://www.youtube-nocookie.com/embed/${preview.youtubeId}?rel=0&modestbranding=1`}
                title={preview.title || "Crashout clip"}
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
              />
            </div>
            <p className="crashout-video-title">{preview.title}</p>
          </div>
        ) : null}
      </div>
    </div>
  );
}

export default AddVideoModal;
