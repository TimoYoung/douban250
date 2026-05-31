<template>
  <div class="version-selector">
    <label>{{ label }}</label>
    <select :value="modelValue" @change="$emit('update:modelValue', $event.target.value === '' ? null : Number($event.target.value))">
      <option v-if="defaultOption" value="">{{ defaultOption }}</option>
      <optgroup v-for="(group, year) in groupedVersions" :key="year" :label="year + '年'">
        <option v-for="v in group" :key="v.id" :value="v.id">
          {{ v.tag }} ({{ v.movie_count }}部)
        </option>
      </optgroup>
    </select>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  versions: { type: Array, default: () => [] },
  modelValue: { type: [Number, null], default: null },
  defaultOption: { type: String, default: '' },
  label: { type: String, default: '版本：' },
})
defineEmits(['update:modelValue'])

const groupedVersions = computed(() => {
  const groups = {}
  for (const v of props.versions) {
    const year = v.tag?.slice(0, 4) || '未知'
    if (!groups[year]) groups[year] = []
    groups[year].push(v)
  }
  // 年份降序，每年内版本也降序
  const sorted = {}
  for (const year of Object.keys(groups).sort((a, b) => b.localeCompare(a))) {
    sorted[year] = groups[year].sort((a, b) => b.tag.localeCompare(a.tag))
  }
  return sorted
})
</script>

<style scoped>
.version-selector {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.version-selector label {
  font-size: 14px;
  color: #666;
}

.version-selector select {
  padding: 6px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-size: 14px;
  min-width: 200px;
}
</style>
