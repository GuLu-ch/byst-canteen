import naive, { dateZhCN, zhCN } from 'naive-ui'
import './admin.css'

/**
 * 管理端专用的 Naive UI 安装器。
 * 按需在路由守卫里 import + 安装，避免把 1MB 的组件库塞进移动端首屏。
 */
let installed = false

export function ensureNaive(app) {
  if (installed || !app) return
  app.use(naive)
  installed = true
}

export const ADMIN_PRIMARY = '#2563eb'

/** 统一的主题变量：中性灰 + 单一蓝，卡片轻阴影，整体克制留白 */
export const themeOverrides = {
  common: {
    primaryColor: ADMIN_PRIMARY,
    primaryColorHover: '#3b7bf0',
    primaryColorPressed: '#1d4ed8',
    primaryColorSuppl: '#3b7bf0',
    borderRadius: '8px',
    borderRadiusSmall: '6px',
    textColorBase: '#111827',
    borderColor: '#eceef2',
    fontFamily:
      "'Inter', 'PingFang SC', 'Microsoft YaHei', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  },
  Card: {
    borderRadius: '12px',
    color: '#ffffff',
    borderColor: '#eceef2',
  },
  Button: {
    borderRadiusMedium: '8px',
  },
  DataTable: {
    thColor: '#f7f8fa',
    thTextColor: '#4b5563',
    thFontWeight: '600',
    borderColor: '#eef0f3',
    tdColorHover: '#f9fafb',
  },
  Menu: {
    itemHeight: '40px',
    itemColorActive: '#eef1f5',
    itemColorActiveHover: '#eef1f5',
    itemTextColorActive: '#0f172a',
    itemTextColorActiveHover: '#0f172a',
    itemIconColorActive: '#0f172a',
    itemIconColorActiveHover: '#0f172a',
  },
  Tag: {
    borderRadius: '6px',
  },
}

export { zhCN, dateZhCN }
