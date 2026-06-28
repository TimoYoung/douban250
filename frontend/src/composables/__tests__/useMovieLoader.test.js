import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { useMovieLoader } from '../useMovieLoader.js'

/**
 * 将 composable 包装为可测试的组件，暴露返回值
 */
function createLoader(fetchFn, options = {}) {
  let result
  const wrapper = mount(
    defineComponent({
      setup() {
        result = useMovieLoader(fetchFn, options)
        return result
      },
      render: () => h('div', { ref: result.sentinelRef }),
    }),
  )
  return { result, wrapper }
}

/**
 * 创建 mock fetch 函数，返回指定的电影数据
 */
function mockFetch(movies, total) {
  return vi.fn().mockResolvedValue({
    data: {
      items: movies,
      total,
      page: 1,
      page_size: movies.length,
      total_pages: 1,
    },
  })
}

const fakeMovies = (count) =>
  Array.from({ length: count }, (_, i) => ({
    id: i + 1,
    title: `Movie ${i + 1}`,
    douban_id: String(i + 1),
  }))

describe('useMovieLoader', () => {
  describe('probe 数据复用（问题 #3）', () => {
    it('total ≤ threshold 且 probe 已返回全部数据时，只发一次请求', async () => {
      const allMovies = fakeMovies(20)
      const fetchFn = mockFetch(allMovies, 20)

      const { result } = createLoader(fetchFn, { threshold: 500, pageSize: 30 })

      await result.loadMovies()

      // 只应发一次请求（probe 的数据足够，不需要 load_all）
      expect(fetchFn).toHaveBeenCalledTimes(1)
      expect(result.movies.value).toHaveLength(20)
      expect(result.total.value).toBe(20)
    })
  })

  describe('不闪白（问题 #2）', () => {
    it('切换筛选时旧数据保留直到新数据到达', async () => {
      // 第一次加载：20 部电影
      const firstMovies = fakeMovies(20)
      const fetchFn = vi.fn()
        .mockResolvedValueOnce({ data: { items: firstMovies, total: 20, page: 1, page_size: 20, total_pages: 1 } })

      const { result } = createLoader(fetchFn, { threshold: 500, pageSize: 30 })
      await result.loadMovies()
      expect(result.movies.value).toHaveLength(20)

      // 第二次加载：使用可控的 promise，验证加载期间旧数据仍存在
      let resolveSecond
      const secondMovies = fakeMovies(10)
      fetchFn.mockReturnValueOnce(
        new Promise((resolve) => { resolveSecond = () => resolve({ data: { items: secondMovies, total: 10, page: 1, page_size: 10, total_pages: 1 } }) })
      )

      // 发起第二次加载（不 await，让它处于 pending 状态）
      const loadPromise = result.loadMovies({ watched_filter: 'watched' })

      // 加载期间，旧数据应该还在（不闪白）
      expect(result.movies.value).toHaveLength(20)
      expect(result.isLoading.value).toBe(true)

      // 解决第二次请求
      resolveSecond()
      await loadPromise

      // 新数据到位后，替换旧数据
      expect(result.movies.value).toHaveLength(10)
      expect(result.total.value).toBe(10)
    })
  })

  describe('请求竞态安全', () => {
    it('连续调用 loadMovies，只有最后一次的结果被应用', async () => {
      // 第一次请求：慢（可控 promise）
      let resolveFirst
      const firstMovies = fakeMovies(100)
      const fetchFn = vi.fn()
        .mockReturnValueOnce(new Promise((r) => { resolveFirst = () => r({ data: { items: firstMovies, total: 100, page: 1, page_size: 100, total_pages: 1 } }) }))

      const { result } = createLoader(fetchFn, { threshold: 500, pageSize: 30 })

      // 发起第一次加载
      const firstLoad = result.loadMovies()

      // 第二次请求：立即返回
      const secondMovies = fakeMovies(5)
      fetchFn.mockResolvedValueOnce({ data: { items: secondMovies, total: 5, page: 1, page_size: 5, total_pages: 1 } })
      const secondLoad = result.loadMovies({ watched_filter: 'watched' })

      await secondLoad

      // 第二次结果应该已经应用
      expect(result.movies.value).toHaveLength(5)
      expect(result.total.value).toBe(5)

      // 解决第一次请求（它的结果应该被丢弃）
      resolveFirst()
      await firstLoad

      // movies 不应该被第一次的结果覆盖
      expect(result.movies.value).toHaveLength(5)
    })
  })

  describe('错误时保留旧数据', () => {
    it('请求失败时不清空已加载的电影', async () => {
      // 第一次加载成功：20 部电影
      const firstMovies = fakeMovies(20)
      const fetchFn = vi.fn()
        .mockResolvedValueOnce({ data: { items: firstMovies, total: 20, page: 1, page_size: 20, total_pages: 1 } })

      const { result } = createLoader(fetchFn, { threshold: 500, pageSize: 30 })
      await result.loadMovies()
      expect(result.movies.value).toHaveLength(20)

      // 第二次加载失败（网络错误）
      fetchFn.mockRejectedValueOnce(new Error('Network error'))
      await result.loadMovies({ watched_filter: 'watched' })

      // 旧数据应保留，不应被清空
      expect(result.movies.value).toHaveLength(20)
      expect(result.total.value).toBe(20)
      // 但 loading 状态应正确结束
      expect(result.isLoading.value).toBe(false)
      // error 应被记录
      expect(result.error.value).toBeTruthy()
    })
  })
})
