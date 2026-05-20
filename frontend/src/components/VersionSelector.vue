<template>
  <div class="version-selector">
    <label>版本：</label>
    <select :value="modelValue" @change="$emit('update:modelValue', Number($event.target.value))">
      <option v-for="v in versions" :key="v.id" :value="v.id">
        {{ v.tag }} ({{ v.movie_count }} 部电影)
      </option>
    </select>
  </div>
</template>

<script setup>
defineProps({
  versions: { type: Array, default: () => [] },
  modelValue: { type: Number, default: null },
})
defineEmits(['update:modelValue'])
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
