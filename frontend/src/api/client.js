// 统一 API 客户端。
// v8：用户端与管理端「账号体系 + 凭证」双分离——
//   用户端（员工）手机号登录，token 存 localStorage `byst_token`；
//   管理端（管理员/厨师）账号密码登录，token 由后端写入 httpOnly cookie，
//   JS 读不到也改不了，两个入口的登录态互不影响。
// 请求头统一用 `Authorization: Bearer`（仅员工端），管理端靠浏览器自动带 cookie。
const APP_TOKEN_KEY = 'byst_token'

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

export function getToken(kind = 'app') {
  if (kind === 'admin') return '' // 管理端凭证在 httpOnly cookie 里，前端不接触
  try {
    return localStorage.getItem(APP_TOKEN_KEY) || ''
  } catch {
    return ''
  }
}

export function setToken(token, kind = 'app') {
  if (kind === 'admin') return
  try {
    if (token) localStorage.setItem(APP_TOKEN_KEY, token)
    else localStorage.removeItem(APP_TOKEN_KEY)
  } catch {
    /* 无痕模式下 localStorage 可能不可用 */
  }
}

let unauthorizedHandler = null
export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = handler
}

const buildQuery = (params) => {
  if (!params) return ''
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') search.append(key, String(value))
  }
  const text = search.toString()
  return text ? `?${text}` : ''
}

const parseError = async (response) => {
  try {
    const data = await response.json()
    const detail = data && data.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail.map((item) => item.msg || '').join('；')
    if (detail) return JSON.stringify(detail)
  } catch {
    /* 忽略解析错误，走通用提示 */
  }
  return '请求失败，请稍后再试'
}

async function request(path, { method = 'GET', body, params, blob = false, form, kind = 'app' } = {}) {
  const token = getToken(kind)
  const headers = {}
  if (token) headers.Authorization = `Bearer ${token}`
  let payload = body
  if (form) {
    payload = form
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
    payload = JSON.stringify(body)
  }
  const response = await fetch(`/api${path}${buildQuery(params)}`, {
    method,
    headers,
    body: payload,
    credentials: 'same-origin',
  })
  if (response.status === 401) {
    if (kind !== 'admin') setToken('', kind)
    if (unauthorizedHandler) unauthorizedHandler(kind)
    throw new ApiError('登录已失效，请重新登录', 401)
  }
  if (!response.ok) throw new ApiError(await parseError(response), response.status)
  if (blob) return response.blob()
  if (response.status === 204) return null
  const text = await response.text()
  return text ? JSON.parse(text) : null
}

export const api = {
  // 管理端页面统一用第三参 'admin'（靠 cookie）；缺省走用户端 localStorage。
  get: (path, params, kind = 'app') => request(path, { params, kind }),
  post: (path, body, kind = 'app') => request(path, { method: 'POST', body, kind }),
  put: (path, body, kind = 'app') => request(path, { method: 'PUT', body, kind }),
  del: (path, kind = 'app') => request(path, { method: 'DELETE', kind }),
  blob: (path, params, kind = 'app') => request(path, { params, blob: true, kind }),
  upload: (path, form, kind = 'app') => request(path, { method: 'POST', form, kind }),
}

export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
