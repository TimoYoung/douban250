<template>
  <div class="pagination-bar">
    <div class="page-size-select">
      <label>每页</label>
      <select :value="pageSize" @change="$emit('update:pageSize', Number($event.target.value))">
        <option :value="10">10</option>
        <option :value="20">20</option>
        <option :value="50">50</option>
        <option :value="100">100</option>
      </select>
      <label>条</label>
    </div>

    <div class="page-controls">
      <button :disabled="page <= 1" @click="$emit('update:page', 1)" title="首页">«</button>
      <button :disabled="page <= 1" @click="$emit('update:page', page - 1)">上一页</button>
      <span class="page-info">{{ page }} / {{ totalPages }}</span>
      <button :disabled="page >= totalPages" @click="$emit('update:page', page + 1)">下一页</button>
      <button :disabled="page >= totalPages" @click="$emit('update:page', totalPages)" title="末页">»</button>
    </div>

    <div class="page-jump">
      <span>跳至</span>
      <input
        type="number"
        class="jump-input"
        min="1"
        :max="totalPages"
        v-model.number="jumpPage"
        @keyup.enter="onJump"
      />
      <button @click="onJump">跳转</button>
    </div>

    <span class="total-info">共 {{ total }} 条</span>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  page: { type: Number, required: true },
  pageSize: { type: Number, required: true },
  totalPages: { type: Number, required: true },
  total: { type: Number, required: true },
})

const emit = defineEmits(['update:page', 'update:pageSize'])

const jumpPage = ref(props.page)

function onJump() {
  const p = Math.max(1, Math.min(jumpPage.value, props.totalPages))
  if (p !== props.page) {
    emit('update:page', p)
  }
  jumpPage.value = p
}
</script>

<style scoped>
.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 16px 0;
  flex-wrap: wrap;
}

.page-size-select {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #666;
}

.page-size-select select {
  padding: 3px 8px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-size: 13px;
}

.page-controls {
  display: flex;
  align-items: center;
  gap: 4px;
}

.page-controls button {
  padding: 4px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
  white-space: nowrap;
}

.page-controls button:hover:not(:disabled) {
  color: #1890ff;
  border-color: #1890ff;
}

.page-controls button:disabled {
  color: #ccc;
  cursor: not-allowed;
}

.page-info {
  font-size: 13px;
  color: #666;
  padding: 0 8px;
  white-space: nowrap;
}

.page-jump {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #666;
}

.jump-input {
  width: 50px;
  padding: 3px 6px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-size: 13px;
  text-align: center;
}

.jump-input::-webkit-inner-spin-button {
  -webkit-appearance: none;
}

.page-jump button {
  padding: 3px 10px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
}

.page-jump button:hover {
  color: #1890ff;
  border-color: #1890ff;
}

.total-info {
  font-size: 13px;
  color: #999;
}
</style>
