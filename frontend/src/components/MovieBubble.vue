<template>
  <div
    class="movie-bubble"
    :class="{ watched: movie.watched, highlighted: isMatch }"
    :title="`#${movie.rank} ${movie.title}`"
    @click="$router.push(`/movies/${movie.douban_id}`)"
  >
    {{ movie.title }}
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  movie: { type: Object, required: true },
  highlight: { type: String, default: '' },
})

const isMatch = computed(() => {
  if (!props.highlight) return false
  return props.movie.title.toLowerCase().includes(props.highlight.toLowerCase())
})
</script>

<style scoped>
.movie-bubble {
  height: 22px;
  line-height: 22px;
  padding: 0 6px;
  border-radius: 3px;
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  transition: transform 0.15s;
  background: #d9d9d9;
  color: #666;
  font-size: 11px;
  white-space: nowrap;
}

.movie-bubble:hover {
  transform: scale(1.2);
  z-index: 10;
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}

.movie-bubble.watched {
  background: #52c41a;
  color: #fff;
}

.movie-bubble.highlighted {
  box-shadow: 0 0 0 2px #6366f1;
  transform: scale(1.1);
}
</style>
