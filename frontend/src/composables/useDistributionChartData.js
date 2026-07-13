import { computed, toValue } from 'vue'

/**
 * 分布图 chart computed 属性 — DashboardView 和 CompareView 共享
 *
 * @param {Ref<object|null>} distribution  — 分布数据源（store 字段或本地 ref）
 * @param {Ref<string>} distTab            — 当前 tab: 'genres' | 'countries' | 'years'
 * @param {Ref<boolean>} isCompare        — 是否为 compare 模式
 * @param {Ref<string>} barColor          — 单模式 bar 颜色
 */
export function useDistributionChartData(distribution, distTab, isCompare, barColor) {
  const labels = computed(() => {
    const data = toValue(distribution)
    if (!data) return []
    const tab = toValue(distTab)
    if (toValue(isCompare)) {
      return data.all_labels?.[tab] || []
    }
    const section = data[tab] || {}
    const entries = Object.entries(section)
    if (tab !== 'years') {
      entries.sort((a, b) => b[1] - a[1])
    }
    return entries.map(e => e[0])
  })

  const doubanValues = computed(() => {
    const data = toValue(distribution)
    if (!data || !toValue(isCompare)) return []
    const tab = toValue(distTab)
    return labels.value.map(l => data.douban[tab]?.[l] || 0)
  })

  const imdbValues = computed(() => {
    const data = toValue(distribution)
    if (!data || !toValue(isCompare)) return []
    const tab = toValue(distTab)
    return labels.value.map(l => data.imdb[tab]?.[l] || 0)
  })

  // singleValues 必须每次求值时检查 isCompare，不能用静态求值（否则模式切换后响应式断裂）
  const singleValues = computed(() => {
    if (toValue(isCompare)) return []
    const data = toValue(distribution)
    if (!data) return []
    const tab = toValue(distTab)
    const section = data[tab] || {}
    return labels.value.map(label => section[label] ?? 0)
  })

  return { labels, doubanValues, imdbValues, singleValues, barColor }
}
