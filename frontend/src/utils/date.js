export const WEEK_LABELS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

export const MEALS = ['breakfast', 'lunch', 'dinner']

export const MEAL_LABELS = { breakfast: '早餐', lunch: '午餐', dinner: '晚餐' }

export const MEAL_ICONS = { breakfast: '🥣', lunch: '🍚', dinner: '🍜' }

export function iso(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

/** 从 Date / 时间戳生成 ISO 日期（供区间组件用） */
export function isoFrom(value) {
  return iso(value instanceof Date ? value : new Date(value))
}

export function parseISO(value) {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, month - 1, day)
}

export function todayISO() {
  return iso(new Date())
}

export function addDays(value, days) {
  const date = typeof value === 'string' ? parseISO(value) : new Date(value)
  date.setDate(date.getDate() + days)
  return iso(date)
}

/** 周一为一周起点 */
export function weekStartOf(value) {
  const date = typeof value === 'string' ? parseISO(value) : new Date(value)
  const offset = (date.getDay() + 6) % 7
  date.setDate(date.getDate() - offset)
  return iso(date)
}

export function weekdayLabel(value) {
  const day = parseISO(value).getDay()
  return WEEK_LABELS[(day + 6) % 7]
}

export function monthDay(value) {
  const date = parseISO(value)
  return `${date.getMonth() + 1}/${date.getDate()}`
}

export function diffDays(from, to) {
  const a = parseISO(from).getTime()
  const b = parseISO(to).getTime()
  return Math.round((b - a) / 86400000)
}

/** 今天 / 明天 / 后天 / 周X */
export function relativeLabel(value) {
  const delta = diffDays(todayISO(), value)
  if (delta === 0) return '今天'
  if (delta === 1) return '明天'
  if (delta === 2) return '后天'
  if (delta === -1) return '昨天'
  return weekdayLabel(value)
}

export function fullDateLabel(value) {
  const date = parseISO(value)
  return `${date.getMonth() + 1}月${date.getDate()}日 ${weekdayLabel(value)}`
}

/** 找到过去最近一次「非未来」的餐次，用于评价页默认日期 */
export function yesterdayISO() {
  return addDays(todayISO(), -1)
}

/* 统一格式：YYYY-MM-DD HH:mm（全站显示口径） */
export function formatDateTime(value) {
  if (!value) return ''
  const str = String(value).replace('T', ' ')
  return str.length >= 16 ? str.slice(0, 16) : str
}

export function formatDate(value) {
  if (!value) return ''
  return String(value).slice(0, 10)
}

/* ---------- 管理端统一的日期区间：今日 / 本周 / 最近30天 ---------- */

export const RANGE_KEYS = ['today', 'week', 'month']

export const RANGE_LABELS = { today: '今日', week: '本周', month: '最近30天' }

/** 某个区间 key → { start, end }（含首尾，ISO 字符串） */
export function rangeOf(key) {
  const today = todayISO()
  if (key === 'today') return { start: today, end: today }
  if (key === 'week') {
    const start = weekStartOf(today)
    return { start, end: addDays(start, 6) }
  }
  return { start: addDays(today, -29), end: today }
}

/** 区间里可展示的自然天数 */
export function daysInRange(start, end) {
  return diffDays(start, end) + 1
}
