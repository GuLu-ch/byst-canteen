import { createRouter, createWebHistory } from 'vue-router'

import { bootstrap, bootstrapAdmin, isAdmin, isStaff, store } from '../stores/app'
import { theme } from '../utils/theme'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/Login.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    component: () => import('../mobile/Layout.vue'),
    children: [
      { path: '', name: 'home', component: () => import('../mobile/Home.vue') },
      { path: 'menu', name: 'menu', component: () => import('../mobile/MenuPage.vue') },
      { path: 'review', name: 'review', component: () => import('../mobile/ReviewPage.vue') },
      { path: 'me', name: 'me', component: () => import('../mobile/Profile.vue') },
      { path: 'feedback', name: 'feedback', component: () => import('../mobile/FeedbackPage.vue') },
      { path: 'vote', name: 'vote', component: () => import('../mobile/VotePage.vue') },
      // 老链接兼容：预约已合并进菜单页
      { path: 'reserve', redirect: '/menu' },
    ],
  },
  {
    // 管理端登录页独立于用户端（凭证用 cookie，互不相通）
    path: '/admin/login',
    name: 'admin-login',
    component: () => import('../views/AdminLogin.vue'),
    meta: { publicAdmin: true },
  },
  {
    path: '/admin',
    component: () => import('../admin/Layout.vue'),
    meta: { staff: true },
    children: [
      { path: '', name: 'admin-dashboard', component: () => import('../admin/Dashboard.vue') },
      { path: 'reservations', name: 'admin-reservations', component: () => import('../admin/Reservations.vue') },
      { path: 'menus', name: 'admin-menus', component: () => import('../admin/Menus.vue') },
      { path: 'feedback', name: 'admin-feedback', component: () => import('../admin/FeedbackView.vue') },
      { path: 'reviews', name: 'admin-reviews', component: () => import('../admin/Reviews.vue') },
      { path: 'votes', name: 'admin-votes', component: () => import('../admin/Votes.vue') },
      {
        path: 'users',
        name: 'admin-users',
        component: () => import('../admin/Users.vue'),
        meta: { adminOnly: true },
      },
      {
        path: 'settings',
        name: 'admin-settings',
        component: () => import('../admin/SettingsView.vue'),
        meta: { adminOnly: true },
      },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach(async (to) => {
  // 管理端固定浅色：用户端切到深色时 html[data-theme=dark] 会把全局文字改成浅色，
  // 管理端的白色卡片就会「白字白底」看不清，所以这里按区域强制主题。
  if (typeof document !== 'undefined') {
    document.documentElement.dataset.theme = to.path.startsWith('/admin') ? 'light' : theme.value
  }

  // 管理端用的 Naive UI 在这里按需安装：必须在组件 setup 之前完成
  if (to.path.startsWith('/admin')) {
    const [{ ensureNaive }, { getApp }] = await Promise.all([
      import('../admin/naive'),
      import('../app-ref'),
    ])
    ensureNaive(getApp())
  }

  if (to.meta.publicAdmin) {
    // 管理端登录页：已登录管理端则直接进后台
    await bootstrapAdmin()
    if (store.admin) return { name: 'admin-dashboard' }
    return true
  }

  if (to.path.startsWith('/admin')) {
    // 管理端区域：校验管理端登录态（员工 token 在这里无效）
    await bootstrapAdmin()
    if (!store.admin) {
      return { name: 'admin-login', query: to.fullPath === '/admin' ? {} : { redirect: to.fullPath } }
    }
    if (to.meta.adminOnly && !isAdmin()) return { name: 'admin-dashboard' }
    return true
  }

  // 用户端区域：校验员工登录态（管理端账号无法从用户端登录）
  await bootstrap()
  if (to.meta.public) {
    if (store.user) return { name: 'home' }
    return true
  }
  if (!store.user) {
    return { name: 'login', query: to.fullPath === '/' ? {} : { redirect: to.fullPath } }
  }
  if (to.meta.staff && !isStaff()) return { name: 'home' }
  return true
})

export default router
