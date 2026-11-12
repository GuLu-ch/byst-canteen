import { computed, ref } from 'vue'

/**
 * 浅色 / 深色主题切换。
 * - 存 localStorage（byst_theme），下次打开保持选择；
 * - 通过 <html data-theme="dark"> 切换 base.css 里的变量集；
 * - 系统偏好首次自动跟随（prefers-color-scheme: dark）。
 */
const KEY = 'byst_theme'

function initial() {
  const saved = localStorage.getItem(KEY)
  if (saved === 'light' || saved === 'dark') return saved
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export const theme = ref(initial())

function apply() {
  document.documentElement.dataset.theme = theme.value
}

// 模块加载时立即应用，避免刷新闪白
apply()

export function setTheme(value) {
  theme.value = value === 'dark' ? 'dark' : 'light'
  localStorage.setItem(KEY, theme.value)
  apply()
}

export function toggleTheme() {
  setTheme(theme.value === 'dark' ? 'light' : 'dark')
}

export function isDark() {
  return theme.value === 'dark'
}

/** 模板里用响应式版本（isDark() 是普通函数，不会触发更新） */
export const isDarkRef = computed(() => theme.value === 'dark')
