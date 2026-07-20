/**
 * Example React component — loads /videos.json and embeds mapped clips.
 * Drop into a React app; not used by the FastAPI app itself (vanilla JS lives in static/crashout-videos.js).
 */
import { useEffect, useMemo, useState } from "react";

async function loadVideos() {
  const res = await fetch("/videos.json");
  if (!res.ok) throw new Error("videos.json missing");
  return res.json();
}

function watchUrl(clip) {
  if (clip.youtubeId) return `https://www.youtube.com/watch?v=${clip.youtubeId}`;
  const q = encodeURIComponent(clip.searchQuery || clip.title || "");
  return `https://www.youtube.com/results?search_query=${q}`;
}

function embedUrl(clip) {
  if (!clip.youtubeId) return null;
  return `https://www.youtube-nocookie.com/embed/${clip.youtubeId}?rel=0&modestbranding=1`;
}

export function CrashoutVideoPlayer({ moduleId = "risk_check", limit = 3 }) {
  const [catalog, setCatalog] = useState({ clips: {}, modules: {} });
  const [error, setError] = useState(null);

  useEffect(() => {
    loadVideos()
      .then(setCatalog)
      .catch((err) => setError(err.message));
  }, []);

  const clips = useMemo(() => {
    const ids = catalog.modules[moduleId] || [];
    return ids
      .map((id) => (catalog.clips[id] ? { id, ...catalog.clips[id] } : null))
      .filter(Boolean)
      .slice(0, limit);
  }, [catalog, moduleId, limit]);

  if (error) return <p className="crashout-video-empty">{error}</p>;
  if (!clips.length) return <p className="crashout-video-empty">No clips for {moduleId}.</p>;

  return (
    <div className="crashout-video-shelf" data-video-module={moduleId}>
      <div className="crashout-video-shelf-grid">
        {clips.map((clip) => {
          const embed = embedUrl(clip);
          const external = watchUrl(clip);
          return (
            <article key={clip.id} className="crashout-video-card" data-video-id={clip.id}>
              <div className={`crashout-video-frame${embed ? "" : " crashout-video-frame--poster"}`}>
                {embed ? (
                  <iframe
                    src={embed}
                    title={clip.title}
                    loading="lazy"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowFullScreen
                  />
                ) : (
                  <>
                    <p className="crashout-video-poster-title">{clip.title}</p>
                    <a className="crashout-video-play" href={external} target="_blank" rel="noopener">
                      Play clip
                    </a>
                  </>
                )}
              </div>
              <div className="crashout-video-meta">
                <p className="crashout-video-title">{clip.title}</p>
                <a className="crashout-video-play crashout-video-play--ghost" href={external} target="_blank" rel="noopener">
                  Open on YouTube
                </a>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}

/** Usage:
 *   <CrashoutVideoPlayer moduleId="spike_alert" />
 *   <CrashoutVideoPlayer moduleId="console_recipes" limit={4} />
 */
export default CrashoutVideoPlayer;
