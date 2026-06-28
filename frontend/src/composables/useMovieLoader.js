import { ref, watch } from 'vue'

/**
 * 混合加载 composable：≤500 条全加载，>500 条无限滚动。
 *
 * 两阶段策略（避免大数据量浪费带宽）：
 *   1. 先请求 page=1&page_size=30 拿到 total
 *   2. total ≤ 500 且数据完整 → 直接使用；total ≤ 500 但数据不全 → load_all 补齐；total > 500 → 逐页追加
 *
 * @param {(params: object) => Promise<{data: PaginatedMovies}>} fetchFn
 *   接收 params 对象，返回 axios response（data 结构为 PaginatedMovies）
 * @param {object} [options]
 * @param {number} [options.threshold=500]  全量加载阈值
 * @param {number} [options.pageSize=30]    无限滚动每页条数
 */
export function useMovieLoader(fetchFn, options = {}) {
  const { threshold = 500, pageSize = 30 } = options

  const movies = ref([])
  const total = ref(0)
  const isLoading = ref(false)
  const isLoadingMore = ref(false)
  const hasMore = ref(false)
  const error = ref(null)

  // IntersectionObserver 目标元素（模板中 ref="sentinelRef" 绑定）
  const sentinelRef = ref(null)

  // 内部状态
  let currentPage = 0
  let requestId = 0       // 防止过期请求污染状态
  let baseParams = {}     // 筛选参数缓存
  let _observer = null    // IntersectionObserver 实例

  // ── 核心加载函数 ──────────────────────────────────────────────

  async function loadMovies(params = {}) {
    const id = ++requestId
    baseParams = params
    isLoading.value = true
    error.value = null
    hasMore.value = false
    currentPage = 0

    try {
      // 第一阶段：用小 page_size 探测 total
      const probeRes = await fetchFn({ ...params, page: 1, page_size: pageSize })
      if (id !== requestId) return
      const probeData = probeRes.data

      if (probeData.total <= threshold) {
        // ── 全加载模式 ──
        if (probeData.items.length >= probeData.total) {
          // probe 已返回全部数据，直接复用（省一次请求）
          movies.value = probeData.items
        } else {
          // probe 数据不全，用 load_all 补齐
          const allRes = await fetchFn({ ...params, load_all: true })
          if (id !== requestId) return
          movies.value = allRes.data.items
        }
        total.value = probeData.total
        hasMore.value = false
      } else {
        // ── 无限滚动模式：首包已在 probeData 中 ──
        movies.value = probeData.items
        total.value = probeData.total
        currentPage = 1
        hasMore.value = probeData.items.length < probeData.total
      }
    } catch (e) {
      if (id !== requestId) return
      error.value = e
      console.error('[useMovieLoader] loadMovies failed:', e)
      // 保留旧数据不清空——请求成功时自然替换，避免瞬时错误导致用户丢失浏览状态
    } finally {
      if (id === requestId) {
        isLoading.value = false
      }
    }
  }

  async function loadMore() {
    if (isLoadingMore.value || !hasMore.value) return

    const id = requestId
    isLoadingMore.value = true
    const nextPage = currentPage + 1

    try {
      const res = await fetchFn({ ...baseParams, page: nextPage, page_size: pageSize })
      if (id !== requestId) return
      const data = res.data

      movies.value.push(...data.items)
      // 触发响应式更新（push 就地修改，Vue 3 对 ref 内部数组的 push 是响应式的）
      currentPage = nextPage
      hasMore.value = movies.value.length < data.total
    } catch (e) {
      if (id !== requestId) return
      error.value = e
      console.error('[useMovieLoader] loadMore failed:', e)
    } finally {
      if (id === requestId) {
        isLoadingMore.value = false
      }
    }
  }

  // ── IntersectionObserver：触底自动加载 ────────────────────────

  watch(
    [sentinelRef, hasMore],
    ([el, more]) => {
      // 清理旧 observer
      if (_observer) {
        _observer.disconnect()
        _observer = null
      }
      if (!el || !more) return

      const observer = new IntersectionObserver(
        (entries) => {
          if (entries[0].isIntersecting && !isLoadingMore.value) {
            loadMore()
          }
        },
        { rootMargin: '200px' },
      )
      observer.observe(el)
      _observer = observer
    },
    { flush: 'post' },
  )

  return {
    movies,
    total,
    isLoading,
    isLoadingMore,
    hasMore,
    error,
    loadMovies,
    loadMore,
    sentinelRef,
  }
}
