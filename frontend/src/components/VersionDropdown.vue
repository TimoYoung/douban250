<template>
  <div class="vd-wrapper" ref="containerRef">
    <button class="vd-trigger" :class="{ open, disabled }" @click="toggle" :disabled="disabled">
      <span class="vd-trigger-text">{{ selectedLabel }}</span>
      <span class="vd-trigger-arrow">▾</span>
    </button>
    <Transition name="vd">
      <div v-if="open && !disabled" class="vd-panel">
        <div class="vd-scroll">
          <div
            v-for="([year, versions]) in grouped"
            :key="year"
            class="vd-year"
          >
            <div class="vd-year-header" @click="toggleYear(year)">
              <span class="vd-year-arrow" :class="{ expanded: expandedYears.has(year) }">▸</span>
              {{ year }}年
              <span class="vd-year-count">({{ versions.length }})</span>
            </div>
            <div v-if="expandedYears.has(year)" class="vd-items">
              <div
                v-for="v in versions"
                :key="v.id"
                class="vd-option"
                :class="{ selected: modelValue === v.id }"
                @click="select(v.id)"
              >
                {{ v.tag }}（{{ v.movie_count }}部）
              </div>
            </div>
          </div>
        </div>
        <div v-if="grouped.length > 1" class="vd-footer" @click="toggleAll">
          {{ allExpanded ? '收起旧版' : '显示全部' }}
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  versions: { type: Array, default: () => [] },
  modelValue: { type: [Number, null], default: null },
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])

const open = ref(false)
const containerRef = ref(null)
const expandedYears = ref(new Set())
const allExpanded = ref(false)

const currentYear = new Date().getFullYear().toString()

const grouped = computed(() => {
  const groups = {}
  for (const v of props.versions) {
    const year = v.tag?.slice(0, 4) || '未知'
    if (!groups[year]) groups[year] = []
    groups[year].push(v)
  }
  const years = Object.keys(groups).sort((a, b) => {
    if (a === '未知') return 1
    if (b === '未知') return -1
    return Number(b) - Number(a)
  })
  return years.map(year => [year, groups[year].sort((a, b) => b.tag.localeCompare(a.tag))])
})

function initExpanded() {
  const years = grouped.value.map(([y]) => y)
  expandedYears.value = new Set(years.filter(y => y === currentYear))
  allExpanded.value = false
}

watch(() => props.versions, initExpanded, { immediate: true })

function toggle() {
  open.value = !open.value
}

function toggleYear(year) {
  const s = new Set(expandedYears.value)
  if (s.has(year)) s.delete(year)
  else s.add(year)
  expandedYears.value = s
  allExpanded.value = grouped.value.every(([y]) => s.has(y))
}

function toggleAll() {
  if (allExpanded.value) {
    initExpanded()
  } else {
    expandedYears.value = new Set(grouped.value.map(([y]) => y))
    allExpanded.value = true
  }
}

function select(id) {
  emit('update:modelValue', id)
  open.value = false
}

const selectedLabel = computed(() => {
  if (props.modelValue == null) return '请选择版本'
  const v = props.versions.find(v => v.id === props.modelValue)
  return v ? `${v.tag}（${v.movie_count}部）` : '请选择版本'
})

function onClickOutside(e) {
  if (containerRef.value && !containerRef.value.contains(e.target)) {
    open.value = false
  }
}
onMounted(() => document.addEventListener('mousedown', onClickOutside))
onBeforeUnmount(() => document.removeEventListener('mousedown', onClickOutside))
</script>

<style scoped>
.vd-wrapper { position: relative; min-width: 200px; }

.vd-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 6px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  background: #fff;
  font-size: 14px;
  cursor: pointer;
  transition: border-color 0.15s;
}
.vd-trigger:hover:not(.disabled) { border-color: #6366f1; }
.vd-trigger.disabled { background: #f5f5f5; color: #999; cursor: not-allowed; }

.vd-trigger-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.vd-trigger-arrow { font-size: 10px; margin-left: 8px; transition: transform 0.2s; color: #999; }
.vd-trigger.open .vd-trigger-arrow { transform: rotate(180deg); }

.vd-panel {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  background: #fff;
  border: 1px solid #e4e4e7;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.1);
  z-index: 100;
  overflow: hidden;
}

.vd-scroll { max-height: 360px; overflow-y: auto; }

.vd-year-header {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 600;
  color: #6366f1;
  background: #f8f8fa;
  cursor: pointer;
  user-select: none;
  position: sticky;
  top: 0;
  z-index: 1;
}
.vd-year-header:hover { background: #f0f0f4; }

.vd-year-arrow { font-size: 10px; transition: transform 0.2s; }
.vd-year-arrow.expanded { transform: rotate(90deg); }
.vd-year-count { color: #a1a1aa; font-weight: 400; margin-left: 2px; }

.vd-items { padding: 2px 0; }

.vd-option {
  padding: 6px 12px 6px 28px;
  font-size: 13px;
  cursor: pointer;
  color: #3f3f46;
  transition: background 0.1s;
}
.vd-option:hover { background: #f4f4f5; }
.vd-option.selected { background: #eef2ff; color: #6366f1; font-weight: 500; }

.vd-footer {
  padding: 8px 12px;
  text-align: center;
  font-size: 12px;
  color: #6366f1;
  border-top: 1px solid #f0f0f2;
  cursor: pointer;
  user-select: none;
}
.vd-footer:hover { background: #f8f8fa; }

.vd-enter-active { transition: opacity 0.15s, transform 0.15s; }
.vd-leave-active { transition: opacity 0.1s, transform 0.1s; }
.vd-enter-from { opacity: 0; transform: translateY(-4px); }
.vd-leave-to { opacity: 0; transform: translateY(-4px); }
</style>
