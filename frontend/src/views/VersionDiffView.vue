<template>
  <div class="version-diff-view">
    <h2>版本对比</h2>

    <div class="diff-controls">
      <div class="control-group">
        <label>当前版本：</label>
        <select v-model="selectedVersion" @change="loadDiff">
          <option v-for="v in versionsStore.versions" :key="v.id" :value="v.id">
            {{ v.tag }}
          </option>
        </select>
      </div>
      <div class="control-group">
        <label>对比版本：</label>
        <select v-model="compareVersion" @change="loadDiff">
          <option :value="null">上一版本</option>
          <option v-for="v in versionsStore.versions" :key="v.id" :value="v.id">
            {{ v.tag }}
          </option>
        </select>
      </div>
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

const versionsStore = useVersionsStore()
const selectedVersion = ref(null)
const compareVersion = ref(null)

onMounted(async () => {
  await versionsStore.loadVersions()
  if (versionsStore.versions.length >= 2) {
    selectedVersion.value = versionsStore.versions[0].id
    compareVersion.value = null
    loadDiff()
  }
})

function loadDiff() {
  if (selectedVersion.value) {
    versionsStore.loadDiff(selectedVersion.value, compareVersion.value)
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

.control-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.control-group label {
  font-size: 13px;
  color: #71717a;
  white-space: nowrap;
  font-weight: 500;
}

.control-group select {
  padding: 6px 12px;
  border: 1px solid #e4e4e7;
  border-radius: 8px;
  font-size: 13px;
  min-width: 140px;
  flex: 1;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.control-group select:focus {
  outline: none;
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
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
  .control-group {
    flex-wrap: nowrap;
  }
  .control-group select {
    min-width: 0;
  }
}
</style>
