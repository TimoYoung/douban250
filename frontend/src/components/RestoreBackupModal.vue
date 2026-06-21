<template>
  <Teleport to="body">
    <div v-if="visible" class="modal-overlay" @click.self="onCancel">
      <div class="modal-box">
        <div class="modal-header">
          <h3>恢复备份</h3>
          <button class="modal-close" @click="onCancel">&times;</button>
        </div>

        <div class="modal-body">
          <!-- 恢复进度 -->
          <div v-if="backupProgress.active && backupProgress.type === 'restore'" class="restore-progress">
            <div class="progress-header">
              <span class="progress-title">正在恢复...</span>
              <span class="progress-percent">{{ backupProgress.percent }}%</span>
            </div>
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: backupProgress.percent + '%' }"></div>
            </div>
            <div class="progress-detail">
              <span>{{ backupProgress.detail || backupProgress.message }}</span>
              <span class="progress-time">已耗时 {{ formatElapsed(backupProgress.elapsed_seconds) }}</span>
            </div>
          </div>

          <!-- 恢复完成 -->
          <div v-else-if="restoreResult && restoreResult.success" class="restore-result">
            <div class="result-icon">✅</div>
            <div class="result-info">
              <p class="result-title">恢复成功！</p>
              <p>模式：{{ restoreResult.mode === 'append' ? '追加' : '覆盖' }}</p>
              <p>电影：导入 {{ restoreResult.movies_imported }} 部，跳过 {{ restoreResult.movies_skipped }} 部</p>
              <p>版本：导入 {{ restoreResult.versions_imported }} 个，跳过 {{ restoreResult.versions_skipped }} 个</p>
              <p>海报：导入 {{ restoreResult.posters_imported }} 张，跳过 {{ restoreResult.posters_skipped }} 张</p>
              <p>耗时：{{ restoreResult.elapsed_seconds }} 秒</p>
            </div>
          </div>

          <!-- 文件选择表单 -->
          <div v-else class="restore-form">
            <div v-if="backupFiles.length === 0" class="empty-backup">
              暂无备份文件
            </div>

            <div v-else class="backup-file-list">
              <label
                v-for="f in backupFiles"
                :key="f.filename"
                class="backup-file-item"
                :class="{ selected: selectedBackupFile === f.filename, corrupted: f.corrupted }"
              >
                <input
                  type="radio"
                  :value="f.filename"
                  v-model="selectedBackupFile"
                  :disabled="f.corrupted"
                />
                <div class="file-info">
                  <div class="file-name">{{ f.filename }}</div>
                  <div class="file-meta">
                    <span>{{ formatSize(f.size) }}</span>
                    <span>{{ f.versions.length }} 个版本</span>
                    <span>{{ f.movie_count }} 部电影</span>
                  </div>
                  <div class="file-versions" v-if="f.versions.length > 0">
                    <span
                      v-for="v in f.versions"
                      :key="v.tag + v.source"
                      class="source-badge"
                      :class="v.source === 'imdb' ? 'source-imdb' : 'source-douban'"
                    >
                      {{ v.source === 'imdb' ? 'IMDb' : '豆瓣' }} {{ v.tag }}
                    </span>
                  </div>
                  <div v-if="f.corrupted" class="file-corrupted">⚠️ 备份文件已损坏</div>
                </div>
                <button
                  class="delete-btn"
                  @click.stop="$emit('delete', f.filename)"
                  title="删除"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                </button>
              </label>
            </div>

            <div v-if="selectedBackupFile" class="restore-options">
              <div class="restore-mode-header">恢复模式：</div>
              <label class="restore-mode-option">
                <input type="radio" value="append" v-model="restoreMode" />
                <div>
                  <div class="mode-label">追加模式</div>
                  <div class="mode-desc">保留现有版本，添加备份中的新版本</div>
                </div>
              </label>
              <label class="restore-mode-option">
                <input type="radio" value="overwrite" v-model="restoreMode" />
                <div>
                  <div class="mode-label">覆盖模式</div>
                  <div class="mode-desc">删除现有版本，用备份数据替换</div>
                </div>
              </label>
              <div v-if="restoreMode === 'overwrite'" class="restore-warning">
                ⚠️ 覆盖模式将删除所有现有版本数据，此操作不可撤销
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button
            v-if="restoreResult && restoreResult.success"
            class="btn btn-dark"
            @click="onClose"
          >
            关闭
          </button>
          <template v-else-if="!(backupProgress.active && backupProgress.type === 'restore')">
            <button class="btn btn-outline" @click="onCancel">取消</button>
            <button
              class="btn btn-dark"
              :disabled="!selectedBackupFile || backupProgress.active"
              @click="onRestore"
            >
              开始恢复
            </button>
          </template>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  visible: Boolean,
  backupFiles: { type: Array, default: () => [] },
  backupProgress: { type: Object, default: () => ({ active: false }) },
  restoreResult: { type: Object, default: null },
})

const emit = defineEmits(['update:visible', 'restore', 'delete', 'close-result'])

const selectedBackupFile = ref('')
const restoreMode = ref('append')

watch(() => props.visible, (val) => {
  if (val) {
    selectedBackupFile.value = ''
    restoreMode.value = 'append'
  }
})

function onCancel() {
  emit('close-result')
  emit('update:visible', false)
}

function onClose() {
  emit('close-result')
  emit('update:visible', false)
}

function onRestore() {
  if (!selectedBackupFile.value) return
  if (restoreMode.value === 'overwrite') {
    if (!confirm('覆盖模式将删除所有现有版本数据，此操作不可撤销。确定继续吗？')) {
      return
    }
  }
  emit('restore', { filename: selectedBackupFile.value, mode: restoreMode.value })
}

function formatSize(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let size = bytes
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024
    i++
  }
  return `${size.toFixed(1)} ${units[i]}`
}

function formatElapsed(seconds) {
  if (!seconds) return '0 秒'
  if (seconds < 60) return `${seconds} 秒`
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins} 分 ${secs} 秒`
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fade-in 0.15s ease;
}

@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes modal-in {
  from { opacity: 0; transform: scale(0.95) translateY(-8px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

.modal-box {
  background: #fff;
  border-radius: 14px;
  width: 520px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  animation: modal-in 0.15s ease;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 0;
}

.modal-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: #18181b;
  margin: 0;
}

.modal-close {
  background: none;
  border: none;
  font-size: 22px;
  color: #a1a1aa;
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
}

.modal-close:hover { color: #52525b; }

.modal-body {
  padding: 20px 24px;
  overflow-y: auto;
  flex: 1;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 16px 24px;
  border-top: 1px solid #f4f4f5;
}

/* Progress */
.restore-progress { margin-bottom: 4px; }
.progress-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.progress-title { font-size: 13px; font-weight: 500; color: #3f3f46; }
.progress-percent { font-size: 13px; font-weight: 600; color: #6366f1; }
.progress-bar { height: 8px; background: #f4f4f5; border-radius: 4px; overflow: hidden; }
.progress-fill { height: 100%; background: linear-gradient(90deg, #6366f1, #818cf8); border-radius: 4px; transition: width 0.3s ease; }
.progress-detail { display: flex; justify-content: space-between; font-size: 12px; color: #71717a; margin-top: 8px; }
.progress-time { color: #a1a1aa; }

/* Result */
.restore-result { display: flex; align-items: flex-start; gap: 16px; padding: 16px; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; }
.result-icon { font-size: 24px; flex-shrink: 0; }
.result-info { flex: 1; }
.result-title { font-size: 14px; font-weight: 600; color: #166534; margin-bottom: 8px; }
.result-info p { font-size: 12px; color: #52525b; margin-bottom: 4px; }

/* Form */
.restore-form { display: flex; flex-direction: column; gap: 12px; }
.empty-backup { text-align: center; padding: 24px; color: #a1a1aa; font-size: 13px; }

/* File list */
.backup-file-list { display: flex; flex-direction: column; gap: 8px; max-height: 300px; overflow-y: auto; }
.backup-file-item { display: flex; align-items: flex-start; gap: 12px; padding: 12px; border: 1px solid #e4e4e7; border-radius: 8px; cursor: pointer; transition: all 0.15s; }
.backup-file-item:hover { border-color: #d4d4d8; background: #fafafa; }
.backup-file-item.selected { border-color: #6366f1; background: #eef2ff; }
.backup-file-item.corrupted { opacity: 0.6; cursor: not-allowed; }
.backup-file-item input[type="radio"] { margin-top: 2px; accent-color: #6366f1; }
.file-info { flex: 1; min-width: 0; }
.file-name { font-size: 13px; font-weight: 500; color: #27272a; margin-bottom: 4px; }
.file-meta { display: flex; gap: 12px; font-size: 11px; color: #71717a; margin-bottom: 6px; }
.file-versions { display: flex; flex-wrap: wrap; gap: 4px; }
.file-corrupted { font-size: 12px; color: #f43f5e; margin-top: 4px; }
.source-badge { display: inline-block; padding: 1px 6px; font-size: 10px; font-weight: 500; border-radius: 4px; }
.source-douban { background: #eef2ff; color: #6366f1; }
.source-imdb { background: #fffbeb; color: #d97706; }

.delete-btn {
  background: none;
  border: none;
  color: #a1a1aa;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  flex-shrink: 0;
}
.delete-btn:hover { color: #ef4444; background: #fef2f2; }

/* Restore options */
.restore-options { padding: 12px 0; border-top: 1px solid #f4f4f5; }
.restore-mode-header { font-size: 13px; font-weight: 500; color: #3f3f46; margin-bottom: 10px; }
.restore-mode-option { display: flex; align-items: flex-start; gap: 10px; padding: 10px 12px; border: 1px solid #e4e4e7; border-radius: 6px; cursor: pointer; margin-bottom: 8px; transition: all 0.15s; }
.restore-mode-option:hover { border-color: #d4d4d8; background: #fafafa; }
.restore-mode-option input[type="radio"] { margin-top: 2px; accent-color: #6366f1; }
.mode-label { font-size: 13px; font-weight: 500; color: #27272a; margin-bottom: 2px; }
.mode-desc { font-size: 12px; color: #71717a; }
.restore-warning { padding: 10px 12px; background: #fff7ed; border: 1px solid #fed7aa; border-radius: 6px; font-size: 12px; color: #9a3412; margin-top: 8px; }

.btn {
  height: 34px;
  padding: 0 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
  border: 1px solid transparent;
}
.btn-dark { background: #18181b; color: #fff; border-color: #18181b; }
.btn-dark:hover { background: #27272a; }
.btn-dark:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-outline { background: #fff; color: #3f3f46; border-color: #e4e4e7; }
.btn-outline:hover { background: #fafafa; border-color: #d4d4d8; }
</style>
