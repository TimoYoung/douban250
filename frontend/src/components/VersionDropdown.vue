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
            v-for="([year, months]) in grouped"
            :key="year"
            class="vd-year"
          >
            <div class="vd-year-header" @click="toggleYear(year)">
              <span class="vd-year-arrow" :class="{ expanded: expandedMonths.has(year) }">▸</span>
              {{ year }}年
              <span class="vd-year-count">({{ yearCount(months) }})</span>
            </div>
            <template v-if="expandedMonths.has(year)">
              <div
                v-for="([month, versions]) in months"
                :key="month"
                class="vd-month"
              >
                <div class="vd-month-header">{{ month }}</div>
                <div class="vd-items">
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
            </template>
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
const expandedMonths = ref(new Map()) // year -> Set(month)
const allExpanded = ref(false)

const MONTH_NAMES = Array.from({ length: 12 }, (_, i) => `${i + 1}月`)
const now = new Date()
const currentYear = now.getFullYear().toString()
const currentMonth = MONTH_NAMES[now.getMonth()]

// grouped: [year, [month, versions[]][]]
const grouped = computed(() => {
  const yearMap = {}
  for (const v of props.versions) {
    const year = v.tag?.slice(0, 4) || '未知'
    const month = v.tag?.slice(5, 7) ? `${Number(v.tag.slice(5, 7))}月` : '未知'
    if (!yearMap[year]) yearMap[year] = {}
    if (!yearMap[year][month]) yearMap[year][month] = []
    yearMap[year][month].push(v)
  }
  const years = Object.keys(yearMap).sort((a, b) => {
    if (a === '未知') return 1
    if (b === '未知') return -1
    return Number(b) - Number(a)
  })
  return years.map(year => {
    const monthKeys = Object.keys(yearMap[year]).sort((a, b) => {
      if (a === '未知') return 1
      if (b === '未知') return -1
      return Number(b.replace('月', '')) - Number(a.replace('月', ''))
    })
    const months = monthKeys.map(m => {
      const sorted = yearMap[year][m].sort((a, b) => b.tag.localeCompare(a.tag))
      return [m, sorted]
    })
    return [year, months]
  })
})

function yearCount(months) {
  return months.reduce((sum, item) => sum + item[1].length, 0)
}

function initExpanded(targetYear, targetMonth) {
  const map = new Map()
  map.set(targetYear, new Set([targetMonth]))
  expandedMonths.value = map
  allExpanded.value = false
}

watch(() => props.versions, () => {
  if (props.modelValue != null) {
    const v = props.versions.find(v => v.id === props.modelValue)
    if (v) {
      const y = v.tag?.slice(0, 4) || currentYear
      const m = v.tag?.slice(5, 7) ? `${Number(v.tag.slice(5, 7))}月` : currentMonth
      initExpanded(y, m)
      return
    }
  }
  initExpanded(currentYear, currentMonth)
}, { immediate: true })

function toggle() {
  open.value = !open.value
}

function toggleYear(year) {
  const map = new Map(expandedMonths.value)
  if (map.has(year)) {
    map.delete(year)
  } else {
    map.set(year, new Set(grouped.value.find(([y]) => y === year)?.[1].map(([m]) => m) || []))
  }
  expandedMonths.value = map
  allExpanded.value = grouped.value.every(([y]) => map.has(y))
}

function toggleAll() {
  if (allExpanded.value) {
    if (props.modelValue != null) {
      const v = props.versions.find(v => v.id === props.modelValue)
      if (v) {
        const y = v.tag?.slice(0, 4) || currentYear
        const m = v.tag?.slice(5, 7) ? `${Number(v.tag.slice(5, 7))}月` : currentMonth
        initExpanded(y, m)
        return
      }
    }
    initExpanded(currentYear, currentMonth)
  } else {
    const map = new Map()
    for (const [year, months] of grouped.value) {
      map.set(year, new Set(months.map(([m]) => m)))
    }
    expandedMonths.value = map
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

.vd-year { position: relative; }

.vd-year-header {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 600;
  color: #6366f1;
  background: #f0f0f4;
  cursor: pointer;
  user-select: none;
  position: sticky;
  top: 0;
  z-index: 2;
}
.vd-year-header:hover { background: #e8e8ee; }

.vd-year-arrow { font-size: 10px; transition: transform 0.2s; }
.vd-year-arrow.expanded { transform: rotate(90deg); }
.vd-year-count { color: #a1a1aa; font-weight: 400; margin-left: 2px; }

.vd-month-header {
  padding: 5px 12px 5px 20px;
  font-size: 11px;
  font-weight: 600;
  color: #71717a;
  background: #f8f8fa;
  user-select: none;
  position: sticky;
  top: 33px;
  z-index: 1;
}

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
