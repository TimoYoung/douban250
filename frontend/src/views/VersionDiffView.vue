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
}

.diff-controls {
  display: flex;
  gap: 24px;
  margin-bottom: 24px;
  background: #fff;
  padding: 16px;
  border-radius: 8px;
}

.control-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.control-group label {
  font-size: 14px;
  color: #666;
  white-space: nowrap;
}

.control-group select {
  padding: 6px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-size: 14px;
  min-width: 160px;
}

.loading, .empty {
  text-align: center;
  padding: 40px;
  color: #999;
  background: #fff;
  border-radius: 8px;
}
</style>
