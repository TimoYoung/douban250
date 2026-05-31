<template>
  <div class="version-diff-view">
    <h2>版本对比</h2>

    <div class="diff-controls">
      <VersionSelector
        :versions="versionsStore.versions"
        v-model="selectedVersion"
        label="当前版本："
        @update:modelValue="loadDiff"
      />
      <VersionSelector
        :versions="versionsStore.versions"
        v-model="compareVersion"
        label="对比版本："
        defaultOption="上一版本"
        @update:modelValue="loadDiff"
      />
    </div>

    <div v-if="versionsStore.loading" class="loading">加载中...</div>
    <VersionDiff v-else-if="versionsStore.diff" :diff="versionsStore.diff" />
    <p v-else-if="versionsStore.diffError" class="empty">{{ versionsStore.diffError }}</p>
    <p v-else class="empty">至少需要两个版本才能进行对比</p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useVersionsStore } from '../stores/versions.js'
import VersionDiff from '../components/VersionDiff.vue'
import VersionSelector from '../components/VersionSelector.vue'

const versionsStore = useVersionsStore()
const selectedVersion = ref(null)
const compareVersion = ref('')

onMounted(async () => {
  await versionsStore.loadVersions()
  if (versionsStore.versions.length >= 2) {
    selectedVersion.value = versionsStore.versions[0].id
    compareVersion.value = ''
    loadDiff()
  }
})

function loadDiff() {
  if (selectedVersion.value) {
    versionsStore.loadDiff(selectedVersion.value, compareVersion.value || null)
  }
}
</script>

<style scoped>
.version-diff-view h2 {
  margin-bottom: 16px;
  font-size: 22px;
  font-weight: 600;
  color: #18181b;
  letter-spacing: -0.3px;
}

.diff-controls {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
  background: #fff;
  padding: 16px 20px;
  border-radius: 12px;
  border: 1px solid rgba(228, 228, 231, 0.6);
  flex-wrap: wrap;
}

.diff-controls :deep(.version-selector) {
  margin-bottom: 0;
}

.loading, .empty {
  text-align: center;
  padding: 40px;
  color: #a1a1aa;
  background: #fff;
  border-radius: 12px;
  border: 1px solid rgba(228, 228, 231, 0.6);
  font-size: 13px;
}

@media (max-width: 640px) {
  .diff-controls {
    flex-direction: column;
    gap: 12px;
    padding: 14px 16px;
  }
}
</style>
