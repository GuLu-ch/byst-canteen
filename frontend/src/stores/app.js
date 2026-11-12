import { reactive } from 'vue'

import { api, getToken, setToken } from '../api/client'
import { isDarkRef, setTheme, theme, toggleTheme } from '../utils/theme'

// 主题能力也从统一入口导出，页面不用各自 import utils/theme
export { isDarkRef as isDark, setTheme, theme, toggleTheme }

// v8：用户端与管理端彻底分离（账号、入口、凭证都分开）。
//   store.user  —— 员工，手机号登录，token 在 localStorage
//   store.admin —— 管理员/厨师，账号密码登录，token 由后端写入 httpOnly cookie
export const store = reactive({
  user: null,
  admin: null,
  settings: null,
  ready: false,
  adminReady: false,
})

export const STAFF_ROLES = ['admin', 'cook']

/** 是否管理端账号（用于管理端界面判断角色） */
export function isStaff() {
  return !!store.admin && STAFF_ROLES.includes(store.admin.role)
}

export function isAdmin() {
  return store.admin?.role === 'admin'
}

export function roleLabel(role) {
  return { admin: '管理员', cook: '厨师', employee: '员工' }[role] || role
}

export async function loadSettings() {
  store.settings = await api.get('/settings/public')
  return store.settings
}

/** 用户端首次进入时恢复登录态 */
export async function bootstrap() {
  if (store.ready) return store
  const tasks = [loadSettings().catch(() => null)]
  if (getToken()) {
    tasks.push(
      api
        .get('/auth/me')
        .then((user) => {
          store.user = user
        })
        .catch(() => setToken('')),
    )
  }
  await Promise.all(tasks)
  store.ready = true
  return store
}

/** 管理端首次进入时恢复登录态（凭证在 httpOnly cookie，浏览器自动携带） */
export async function bootstrapAdmin() {
  if (store.adminReady) return store
  const tasks = [loadSettings().catch(() => null)]
  tasks.push(
    api
      .get('/auth/admin-me', null, 'admin')
      .then((user) => {
        store.admin = user
      })
      .catch(() => {
        store.admin = null
      }),
  )
  await Promise.all(tasks)
  store.adminReady = true
  return store
}

/** 员工端登录（管理端账号会被后端拒绝） */
export async function login(phone, password) {
  const data = await api.post('/auth/login', { phone, password })
  setToken(data.token)
  store.user = data.user
  return data.user
}

/** 管理端登录：账号 + 密码（员工账号会被后端拒绝，凭证落到 httpOnly cookie） */
export async function adminLogin(account, password) {
  const data = await api.post('/auth/admin-login', { account, password }, 'admin')
  store.admin = data.user
  store.adminReady = true
  return data.user
}

/** 退出员工端登录 */
export function logout() {
  setToken('')
  store.user = null
}

/** 退出管理端登录：通知后端清 cookie，并清掉本地状态 */
export async function adminLogout() {
  try {
    await api.post('/auth/admin-logout', undefined, 'admin')
  } catch {
    /* cookie 已失效时忽略 */
  }
  store.admin = null
  store.adminReady = false
}
