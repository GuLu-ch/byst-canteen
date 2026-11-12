import { onBeforeUnmount, onMounted, ref } from 'vue'

/**
 * 管理端响应式：判断当前是否为窄屏（默认 < 900px，覆盖横屏手机与竖屏平板）。
 * 用 matchMedia 而不是监听 resize，性能更好，也能在挂载时立刻得到正确值。
 *
 * 注意：SSR / jsdom 里 matchMedia 可能是简化实现，这里做了兜底。
 */
export function useIsMobile(maxWidth = 900) {
  const query = `(max-width: ${maxWidth}px)`
  const read = () => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return false
    return window.matchMedia(query).matches
  }
  const isMobile = ref(read())
  let mql = null

  const onChange = (event) => {
    isMobile.value = event.matches
  }

  onMounted(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return
    mql = window.matchMedia(query)
    isMobile.value = mql.matches
    // Safari < 14 只有 addListener
    if (mql.addEventListener) mql.addEventListener('change', onChange)
    else if (mql.addListener) mql.addListener(onChange)
  })

  onBeforeUnmount(() => {
    if (!mql) return
    if (mql.removeEventListener) mql.removeEventListener('change', onChange)
    else if (mql.removeListener) mql.removeListener(onChange)
  })

  return isMobile
}
