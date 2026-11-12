/**
 * 用 jsdom 在 Node 里把构建产物跑起来，逐个路由检查页面是否真正渲染、有没有运行时错误。
 *
 * 为什么不用浏览器：本机沙箱禁止管道 stdio / 具名管道，Chrome 的 crashpad 起不来，
 * headless Chrome 一启动就退出（crashpad_client_win.cc: OpenProcess 拒绝访问 0x5）；
 * Playwright 启动 driver 也需要管道，PermissionError: [WinError 5]。
 * jsdom 足够检查「模板是否报错、接口是否取到数据、关键文案是否出现」。
 *
 * 前置条件：
 *   1. 后端运行在 127.0.0.1:8000（`uvicorn app.main:app`）
 *   2. `node scripts/build_test.mjs` 已生成 frontend/dist-test（base=./、关闭 modulePreload）
 * 用法：
 *   node scripts/dom_check.mjs            # 全部路由
 *   ONLY_ROUTE=/ node scripts/dom_check.mjs
 */

import fs from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'
import { pathToFileURL } from 'node:url'

const ROOT = path.resolve(import.meta.dirname, '..')
const require = createRequire(path.join(ROOT, 'frontend', 'package.json'))
const { JSDOM } = require('jsdom')
const TEST_DIST = path.join(ROOT, 'frontend', 'dist-test')
const DIST = fs.existsSync(path.join(TEST_DIST, 'index.html')) ? TEST_DIST : path.join(ROOT, 'frontend', 'dist')
const BASE = 'http://127.0.0.1:8000'

// Node 24 的 fetch 在进程启动时就读了代理配置，这里删掉只是保险
for (const key of Object.keys(process.env)) {
  if (key.toLowerCase().includes('proxy')) delete process.env[key]
}

const PAGES = [
  ['/admin/login', 'admin-login', null, ['管理后台', '账号', '密码', '进入后台'], 12000],
  ['/', 'mobile-home', '13800000012', ['明日三餐', '本周菜单', '本周最爱菜投票', '食堂意见反馈']],
  ['/vote', 'mobile-vote', '13800000012', ['本周最爱菜投票', '排行榜']],
  ['/menu', 'mobile-menu', '13800000012', ['本日已选', '全选本日', '同上一周', '预约截止']],
  ['/review', 'mobile-review', '13800000012', ['菜品评价', '非常好', '午餐评价']],
  ['/feedback', 'mobile-feedback', '13800000012', ['意见反馈', '匿名']],
  ['/me', 'mobile-profile', '13800000012', ['我的口味档案', '我的预约', '意见反馈', '切换深色模式']],
  ['/admin', 'admin-dashboard', 'admin', ['预约趋势', '区间最爱菜排行'], 24000],
  ['/admin/reservations', 'admin-reservations', 'admin', ['每日就餐人数', '导出 Excel', '区间总人次'], 24000],
  ['/admin/menus', 'admin-menus', 'admin', ['复制上周', '导出模板', '导入菜单', '（本周）'], 24000],
  ['/admin/feedback', 'admin-feedback', 'admin', ['反馈类型分布', '反馈列表', '区间反馈'], 24000],
  ['/admin/reviews', 'admin-reviews', 'admin', ['评分分布', '不满意原因统计', '每天平均分趋势'], 24000],
  ['/admin/votes', 'admin-votes', 'admin', ['投票排行', '参与率'], 24000],
  ['/admin/users', 'admin-users', 'admin', ['员工总数', '批量导入'], 24000],
  ['/admin/settings', 'admin-settings', 'admin', ['功能开关', '可预约天数'], 24000],
]

const nodeFetch = globalThis.fetch
// jsdom 里解析 Element Plus（782KB）与 ECharts（1.1MB）比浏览器慢得多，默认多等一会儿再判定。
const WAIT_MS = Number(process.env.WAIT_MS || 6000)

process.on('unhandledRejection', (reason) => {
  console.log(`     [node unhandledRejection] ${(reason && (reason.stack || reason.message)) || reason}`.slice(0, 900))
})
process.on('uncaughtException', (error) => {
  console.log(`     [node uncaughtException] ${error.stack || error}`.slice(0, 900))
})

async function login(value, scope = 'app') {
  const path = scope === 'admin' ? '/api/auth/admin-login' : '/api/auth/login'
  const body =
    scope === 'admin'
      ? { account: value, password: '123456' }
      : { phone: value, password: '123456' }
  const response = await nodeFetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) throw new Error(`登录失败 ${value}(${scope}): ${response.status}`)
  if (scope === 'admin') {
    // v8：管理端凭证由后端写入 httpOnly cookie，jsdom 里取出来改用 Authorization 头
    const raw = (response.headers.getSetCookie?.() || [response.headers.get('set-cookie')])
      .filter(Boolean)
      .join('; ')
    const match = /byst_admin=([^;]+)/.exec(raw)
    if (!match) throw new Error('管理端登录未返回 cookie')
    return decodeURIComponent(match[1])
  }
  return (await response.json()).token
}

const html = fs.readFileSync(path.join(DIST, 'index.html'), 'utf8')
const entryMatch = html.match(/src="([^"]*index-[^"]+\.js)"/)
if (!entryMatch) throw new Error('未在 index.html 找到入口脚本')
const ENTRY = path.join(DIST, entryMatch[1].replace(/^\.?\//, ''))

let round = 0

function installDom(url, tokenValue, errors, scope = 'app') {
  const dom = new JSDOM('<!DOCTYPE html><html><body><div id="app"></div></body></html>', {
    url,
    pretendToBeVisual: true,
    // Vite 的动态 import 会等 CSS <link> 的 load 事件，jsdom 默认不加载资源就会一直挂住
    resources: 'usable',
  })
  const { window } = dom

  for (const key of ['document', 'navigator', 'location', 'history', 'localStorage']) {
    Object.defineProperty(globalThis, key, { value: window[key], configurable: true, writable: true })
  }
  globalThis.window = window
  for (const key of [
    'HTMLElement', 'Element', 'Node', 'SVGElement', 'NodeList', 'DocumentFragment', 'Image',
    'HTMLCanvasElement', 'HTMLInputElement', 'HTMLTextAreaElement', 'HTMLSelectElement',
    'Event', 'CustomEvent', 'MouseEvent', 'KeyboardEvent', 'TouchEvent', 'FocusEvent', 'InputEvent',
    'WheelEvent', 'MutationObserver', 'DOMParser', 'XMLSerializer',
  ]) {
    Object.defineProperty(globalThis, key, { value: window[key], configurable: true, writable: true })
  }
  globalThis.getComputedStyle = window.getComputedStyle.bind(window)
  globalThis.requestAnimationFrame = window.requestAnimationFrame.bind(window)
  globalThis.cancelAnimationFrame = window.cancelAnimationFrame.bind(window)

  window.ResizeObserver = globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  window.IntersectionObserver = globalThis.IntersectionObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
    takeRecords() {
      return []
    }
  }
  window.matchMedia =
    window.matchMedia ||
    ((query) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener() {},
      removeListener() {},
      addEventListener() {},
      removeEventListener() {},
      dispatchEvent() {
        return false
      },
    }))

  // MOBILE_ADMIN=1：把管理端伪装成窄屏，用来验证手机端布局（抽屉导航 / 卡片列表）
  if (process.env.MOBILE_ADMIN === '1' && scope === 'admin') {
    const mobileMql = (query) => ({
      matches: /max-width/.test(String(query)),
      media: String(query),
      onchange: null,
      addListener() {},
      removeListener() {},
      addEventListener() {},
      removeEventListener() {},
      dispatchEvent() {
        return false
      },
    })
    window.matchMedia = mobileMql
    globalThis.matchMedia = mobileMql
  }
  window.scrollTo = () => {}
  if (!window.requestIdleCallback) window.requestIdleCallback = (cb) => window.setTimeout(cb, 1)
  window.matchMedia = window.matchMedia || globalThis.matchMedia
  // jsdom 没有实现 canvas 2d 上下文。ECharts 初始化时会大量读写 ctx 属性，
  // 直接返回 null 会抛 "Cannot set properties of null (setting 'dpr')"，
  // 所以给一个「任何属性可读可写、任何方法都是空函数」的假上下文。
  globalThis.matchMedia = globalThis.matchMedia || window.matchMedia
  const fakeCtx = () =>
    new Proxy(
      {},
      {
        get(target, key) {
          if (key in target) return target[key]
          if (key === 'canvas') return { width: 800, height: 400, style: {} }
          if (key === 'measureText') return () => ({ width: 10 })
          if (key === 'createLinearGradient' || key === 'createRadialGradient' || key === 'createPattern') {
            return () => ({ addColorStop() {} })
          }
          if (key === 'getImageData' || key === 'createImageData') {
            return (x, y, w, h) => ({ data: new Uint8ClampedArray((w || 1) * (h || 1) * 4) })
          }
          if (key === 'isPointInPath' || key === 'isPointInStroke') return () => false
          if (key === 'getLineDash') return () => []
          return () => {}
        },
        set(target, key, value) {
          target[key] = value
          return true
        },
      },
    )
  window.HTMLCanvasElement.prototype.getContext = () => fakeCtx()

  window.addEventListener('error', (event) => {
    errors.push(`[window.error] ${event.message} @ ${event.filename}:${event.lineno}`)
  })
  window.addEventListener('unhandledrejection', (event) => {
    const reason = event.reason
    errors.push(`[unhandledrejection] ${reason && (reason.stack || reason.message || reason)}`)
  })
  // jsdom 里 el-table 量不到布局，单元格插槽会被以空 props 调用而抛错；浏览器中有真实布局不会走到这条路径，
  // 这里只忽略这两条已知的假阳性，其它错误照常计入。
  const KNOWN_JSDOM_NOISE = [/Cannot destructure property 'row'/, /Cannot read properties of undefined \(reading 'row'\)/]
  const pushError = (prefix, args) => {
    const message = args.map(String).join(' ')
    if (KNOWN_JSDOM_NOISE.some((pattern) => pattern.test(message))) return
    errors.push(`${prefix} ${message}`)
  }
  window.console.error = (...args) => pushError('[console.error]', args)
  window.console.warn = (...args) => pushError('[console.warn]', args)

  globalThis.fetch = (input, init = {}) => {
    const raw = typeof input === 'string' ? input : String((input && (input.url || input)) || '')
    if (!/^https?:/i.test(raw) && !raw.startsWith('/')) {
      return Promise.resolve({ ok: true, text: async () => '', arrayBuffer: async () => new ArrayBuffer(0) })
    }
    const options = { ...init }
    if (scope === 'admin' && tokenValue) {
      // jsdom 不会自动带 cookie，这里用后端同样支持的 Authorization 头传管理端 token
      options.headers = { ...(init.headers || {}), Authorization: `Bearer ${tokenValue}` }
    }
    return nodeFetch(new URL(raw, BASE), options)
  }

  if (scope === 'admin' && tokenValue) {
    // v8：管理端不把 token 放到 JS 能读的地方，这里只用于本脚本的请求头注入
    window.document.cookie = `byst_admin=${tokenValue}; path=/`
  } else if (scope !== 'admin') {
    window.localStorage.setItem('byst_token', tokenValue)
  }
  return dom
}

async function checkPage([route, name, phone, expected, waitOverride]) {
  const errors = []
  const scope = route.startsWith('/admin') ? 'admin' : 'app'
  // phone 为 null 表示不需要登录（管理端登录页本身）
  const value = phone === null ? '' : await login(phone, scope)
  const dom = installDom(BASE + route, value, errors, scope)
  // 先导入任意一个懒加载 chunk 预热 ESM 模块图：经验证，若直接导入入口模块，
  // 路由守卫后的首次动态 import 在 jsdom 里永远不会完成（#app 只剩 <!---->）。
  if (!process.env.SKIP_CHUNK_WARMUP) {
    const assets = fs.readdirSync(path.join(DIST, 'assets'))
    const preferred = route.startsWith('/admin') ? 'Dashboard-' : 'Home-'
    const chunk = assets.find((file) => file.startsWith(preferred) && file.endsWith('.js')) ||
      assets.find((file) => file.startsWith('Home-') && file.endsWith('.js'))
    if (chunk) {
      try {
        await import(pathToFileURL(path.join(DIST, 'assets', chunk)).href)
      } catch (error) {
        errors.push(`[warmup ${chunk}] ${error.stack || error}`)
      }
    }
  }
  round += 1
  try {
    await import(`${pathToFileURL(ENTRY).href}?round=${round}`)
  } catch (error) {
    errors.push(`[import] ${error.stack || error}`)
  }
  await new Promise((resolve) => setTimeout(resolve, waitOverride || WAIT_MS))
  const readText = () => (dom.window.document.body.textContent || '').replace(/\s+/g, ' ').trim()
  let text = readText()
  let missing = expected.filter((word) => !text.includes(word))
  // 数据接口与懒加载 chunk 都是异步的，首屏文案可能晚一拍到位；
  // 缺文案时逐步追加等待复核，避免 jsdom 解析大 chunk（Naive UI + ECharts）时的假失败。
  for (const extra of [5000, 8000, 12000]) {
    if (!missing.length) break
    await new Promise((resolve) => setTimeout(resolve, extra))
    text = readText()
    missing = expected.filter((word) => !text.includes(word))
  }
  const app = dom.window.document.querySelector('#app')
  const appHtml = (app && app.innerHTML) || ''
  const status = errors.length === 0 && missing.length === 0 ? 'OK ' : 'ERR'
  console.log(`${status} ${route.padEnd(22)} ${name.padEnd(20)} ${text.slice(0, 80)}`)
  if (!appHtml || appHtml === '<!---->') console.log(`     #app 未渲染: ${appHtml || '(空)'}`)
  if (process.env.DEBUG_TEXT) {
    console.log(
      `     [nav] items=${dom.window.document.querySelectorAll('.n-menu-item').length} dots=${dom.window.document.querySelectorAll('.nav-dot, .nav-ico-dot').length} toggle=${dom.window.document.querySelectorAll('.nav-toggle').length}`,
    )
    console.log(
      `     [view] fbCards=${dom.window.document.querySelectorAll('.fb-card').length} dayItems=${dom.window.document.querySelectorAll('.day-item').length} dayCards=${dom.window.document.querySelectorAll('.day-card').length} tables=${dom.window.document.querySelectorAll('.n-data-table').length}`,
    )
    // 手机端：点一下汉堡按钮，确认抽屉里的导航能正常渲染
    if (process.env.MOBILE_ADMIN === '1') {
      const toggle = dom.window.document.querySelector('.nav-toggle')
      if (toggle) {
        toggle.click()
        await new Promise((resolve) => setTimeout(resolve, 900))
        console.log(
          `     [drawer] open=${dom.window.document.querySelectorAll('.n-drawer').length} items=${dom.window.document.querySelectorAll('.n-drawer .n-menu-item').length}`,
        )
      }
    }
    const html = dom.window.document.querySelector('.n-card-header__main')
    console.log(
      `     [len ${text.length}] cards=${dom.window.document.querySelectorAll('.n-card').length} headers=${dom.window.document.querySelectorAll('.n-card-header__main').length}`,
    )
    if (html) console.log(`     [first header] ${html.outerHTML.slice(0, 200)}`)
    console.log(`     [text] ${text}`)
  }
  if (missing.length) console.log(`     缺少文案: ${missing.join(', ')}`)
  for (const item of [...new Set(errors)]) console.log(`     ${item.slice(0, 400)}`)
  dom.window.close()
  return errors.length + missing.length
}

// 每个路由必须跑在独立进程里：ESM 模块缓存是按 URL 缓存的，而共享 chunk（router/stores/client）
// 的 URL 里没有查询串，第二个页面会复用到第一个页面的 Vue Router 单例（绑定在已关闭的 window 上），
// 结果页面永远是空注释 <!---->。
const childRoute = process.env.DOM_CHILD_ROUTE
if (childRoute) {
  const page = PAGES.find((item) => item[0] === childRoute)
  const problems = await checkPage(page)
  process.exit(problems === 0 ? 0 : 1)
}

const { spawnSync } = await import('node:child_process')
const only = process.env.ONLY_ROUTE
const targets = only ? PAGES.filter((item) => item[0] === only) : PAGES
let failed = 0
for (const [route, , , , waitOverride] of targets) {
  const result = spawnSync(process.execPath, [import.meta.filename], {
    stdio: 'inherit',
    env: { ...process.env, DOM_CHILD_ROUTE: route, ...(waitOverride ? { WAIT_MS: String(waitOverride) } : {}) },
  })
  if (result.status !== 0) failed += 1
}
console.log(`\n${targets.length} 个路由，失败 ${failed} 个`)
process.exit(failed === 0 ? 0 : 1)
