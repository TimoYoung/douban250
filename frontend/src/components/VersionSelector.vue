<template>
  <div class="version-selector">
    <div v-if="sources.length > 1" class="source-tabs">
      <button
        v-for="s in sources"
        :key="s"
        class="source-tab"
        :class="{ active: sourceFilter === s }"
        @click="$emit('update:sourceFilter', s)"
      >{{ sourceLabels[s] || s }}</button>
    </div>
    <label>{{ label }}</label>
    <VersionDropdown
      :versions="versions"
      :modelValue="modelValue"
      @update:modelValue="$emit('update:modelValue', $event)"
    />
  </div>
</template>

<script setup>
import VersionDropdown from './VersionDropdown.vue'

defineProps({
  versions: { type: Array, default: () => [] },
  modelValue: { type: [Number, null], default: null },
  label: { type: String, default: '版本：' },
  sourceFilter: { type: String, default: 'douban' },
  sources: { type: Array, default: () => [] },
})
defineEmits(['update:modelValue', 'update:sourceFilter'])

const sourceLabels = { douban: '豆瓣', imdb: 'IMDb' }
</script>

<style scoped>
.version-selector {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.source-tabs { display: flex; gap: 0; }

.source-tab {
  padding: 4px 12px;
  border: 1px solid #e4e4e7;
  background: #fff;
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  color: #71717a;
  transition: all 0.15s;
}
.source-tab:first-child { border-radius: 6px 0 0 6px; }
.source-tab:last-child { border-radius: 0 6px 6px 0; border-left: none; }
.source-tab.active { background: #6366f1; color: #fff; border-color: #6366f1; }
.source-tab:hover:not(.active) { background: #fafafa; color: #3f3f46; }

.version-selector label { font-size: 14px; color: #666; }
</style>
