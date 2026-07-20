<!--
  Example Vue 3 SFC — loads /videos.json and embeds mapped clips.
  Mirror of static/crashout-videos.js for teams using Vue.
-->
<script setup>
import { computed, onMounted, ref } from "vue";

const props = defineProps({
  moduleId: { type: String, default: "risk_check" },
  limit: { type: Number, default: 3 },
});

const catalog = ref({ clips: {}, modules: {} });
const error = ref(null);

function watchUrl(clip) {
  if (clip.youtubeId) return `https://www.youtube.com/watch?v=${clip.youtubeId}`;
  const q = encodeURIComponent(clip.searchQuery || clip.title || "");
  return `https://www.youtube.com/results?search_query=${q}`;
}

function embedUrl(clip) {
  if (!clip.youtubeId) return null;
  return `https://www.youtube-nocookie.com/embed/${clip.youtubeId}?rel=0&modestbranding=1`;
}

const clips = computed(() => {
  const ids = catalog.value.modules[props.moduleId] || [];
  return ids
    .map((id) => (catalog.value.clips[id] ? { id, ...catalog.value.clips[id] } : null))
    .filter(Boolean)
    .slice(0, props.limit);
});

onMounted(async () => {
  try {
    const res = await fetch("/videos.json");
    if (!res.ok) throw new Error("videos.json missing");
    catalog.value = await res.json();
  } catch (err) {
    error.value = err.message || "Failed to load videos";
  }
});
</script>

<template>
  <p v-if="error" class="crashout-video-empty">{{ error }}</p>
  <p v-else-if="!clips.length" class="crashout-video-empty">No clips for {{ moduleId }}.</p>
  <div v-else class="crashout-video-shelf" :data-video-module="moduleId">
    <div class="crashout-video-shelf-grid">
      <article
        v-for="clip in clips"
        :key="clip.id"
        class="crashout-video-card"
        :data-video-id="clip.id"
      >
        <div
          class="crashout-video-frame"
          :class="{ 'crashout-video-frame--poster': !embedUrl(clip) }"
        >
          <iframe
            v-if="embedUrl(clip)"
            :src="embedUrl(clip)"
            :title="clip.title"
            loading="lazy"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowfullscreen
          />
          <template v-else>
            <p class="crashout-video-poster-title">{{ clip.title }}</p>
            <a class="crashout-video-play" :href="watchUrl(clip)" target="_blank" rel="noopener">
              Play clip
            </a>
          </template>
        </div>
        <div class="crashout-video-meta">
          <p class="crashout-video-title">{{ clip.title }}</p>
          <a
            class="crashout-video-play crashout-video-play--ghost"
            :href="watchUrl(clip)"
            target="_blank"
            rel="noopener"
          >
            Open on YouTube
          </a>
        </div>
      </article>
    </div>
  </div>
</template>

<!-- Usage:
  <CrashoutVideoPlayer module-id="spike_alert" />
  <CrashoutVideoPlayer module-id="console_recipes" :limit="4" />
-->
