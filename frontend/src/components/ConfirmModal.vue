<template>
  <Teleport to="body">
    <div v-if="visible" class="modal-overlay" @click.self="onCancel">
      <div class="modal-box">
        <div class="modal-header">
          <h3>{{ title }}</h3>
        </div>
        <div class="modal-body">
          <slot />
        </div>
        <div class="modal-footer">
          <button class="btn btn-cancel" @click="onCancel">取消</button>
          <button class="btn btn-danger" @click="onConfirm" :disabled="confirmLoading">
            {{ confirmLoading ? '处理中…' : confirmText }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
defineProps({
  visible: { type: Boolean, default: false },
  title: { type: String, default: '确认操作' },
  confirmText: { type: String, default: '确定' },
  confirmLoading: { type: Boolean, default: false },
})

const emit = defineEmits(['cancel', 'confirm'])

function onCancel() { emit('cancel') }
function onConfirm() { emit('confirm') }
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(2px);
}

.modal-box {
  background: #fff;
  border-radius: 14px;
  width: 420px;
  max-width: 90vw;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  overflow: hidden;
  animation: modal-in 0.15s ease-out;
}

@keyframes modal-in {
  from { opacity: 0; transform: scale(0.95) translateY(-8px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

.modal-header {
  padding: 20px 24px 0;
}

.modal-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #18181b;
}

.modal-body {
  padding: 16px 24px;
  font-size: 13px;
  color: #52525b;
  line-height: 1.6;
}

.modal-footer {
  padding: 12px 24px 20px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.btn {
  padding: 7px 18px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid #e4e4e7;
  font-family: inherit;
  transition: all 0.15s;
}

.btn-cancel {
  background: #fff;
  color: #3f3f46;
}

.btn-cancel:hover { background: #f4f4f5; }

.btn-danger {
  background: #ef4444;
  color: #fff;
  border-color: #ef4444;
}

.btn-danger:hover { background: #dc2626; }
.btn-danger:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
