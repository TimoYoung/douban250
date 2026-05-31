<template>
  <div class="bubble-grid">
    <MovieBubble v-for="movie in movies" :key="movie.douban_id" :movie="movie" :highlight="highlight" />
  </div>
</template>

<script setup>
import MovieBubble from './MovieBubble.vue'

defineProps({
  movies: { type: Array, required: true },
  highlight: { type: String, default: '' },
})
</script>

<style scoped>
.bubble-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 3px 2px;
  padding: 12px;
  background: #fff;
  border-radius: 8px;
}
</style>
