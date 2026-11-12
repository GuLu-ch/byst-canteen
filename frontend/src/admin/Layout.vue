<script setup>
// 管理端布局：纯白侧栏 + 极简顶栏（无深色模式、无重色块），重点保证文字对比度。
import { computed, h, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  NDialogProvider,
  NDropdown,
  NIcon,
  NLayout,
  NLayoutContent,
  NLayoutSider,
  NMenu,
  NMessageProvider,
} from 'naive-ui'
import { RouterLink } from 'vue-router'
import {
  CalendarClearOutline,
  ChatbubbleEllipsesOutline,
  ChevronBackOutline,
  CloseOutline,
  GridOutline,
  HeartOutline,
  PeopleOutline,
  PulseOutline,
  RefreshOutline,
  RestaurantOutline,
  SettingsOutline,
  StarOutline,
} from '@vicons/ionicons5'

import { dateZhCN, themeOverrides, zhCN } from './naive'
import { adminLogout, isAdmin, roleLabel, store } from '../stores/app'
import { pendingFeedback, refreshPendingFeedback } from '../stores/adminBadges'

const route = useRoute()
const router = useRouter()

const collapsed = ref(localStorage.getItem('byst_admin_collapsed') === '1')
const refreshKey = ref(0)

watch(collapsed, (value) => localStorage.setItem('byst_admin_collapsed', value ? '1' : '0'))

const item = (label, key, iconComponent, options = {}) => {
  const withDot = !!options.dot
  const show = () => withDot && pendingFeedback.value > 0
  // 小红点存在时，点菜单直接进入「全部待处理」列表（不限日期区间）
  const target = () => (withDot && pendingFeedback.value > 0 ? { path: key, query: { handled: 'false' } } : { path: key })
  return {
    label: () =>
      h(RouterLink, { to: target() }, {
        default: () => [label, show() ? h('span', { class: 'nav-dot', title: `${pendingFeedback.value} 条待处理反馈` }) : null],
      }),
    key,
    icon: () =>
      h('span', { class: 'menu-ico' }, [
        h(NIcon, null, { default: () => h(iconComponent) }),
        // 收起导航时只剩图标，小红点挪到图标右上角
        show() && collapsed.value
          ? h('i', { class: 'nav-ico-dot', title: `${pendingFeedback.value} 条待处理反馈` })
          : null,
      ]),
  }
}

const menuOptions = computed(() => {
  const items = [
    item('数据概览', '/admin', PulseOutline),
    item('就餐预约', '/admin/reservations', CalendarClearOutline),
    item('菜单管理', '/admin/menus', RestaurantOutline),
    item('意见反馈', '/admin/feedback', ChatbubbleEllipsesOutline, { dot: true }),
    item('菜品评价', '/admin/reviews', StarOutline),
    item('最爱菜投票', '/admin/votes', HeartOutline),
  ]
  if (isAdmin()) {
    items.push(item('员工管理', '/admin/users', PeopleOutline))
    items.push(item('系统设置', '/admin/settings', SettingsOutline))
  }
  return items
})

/** 底部收起/展开导航：作为独立菜单项渲染，几何尺寸与上面的导航完全一致 */
const collapseOptions = computed(() => [
  {
    key: 'toggle-collapse',
    label: collapsed.value ? '展开导航' : '收起导航',
    icon: () =>
      h('span', { class: 'menu-ico' }, [
        h(NIcon, null, { default: () => h(collapsed.value ? GridOutline : ChevronBackOutline) }),
      ]),
  },
])

function onMenuSelect(key) {
  if (key === 'toggle-collapse') collapsed.value = !collapsed.value
}

onMounted(refreshPendingFeedback)
// 每次切页刷新一下待处理数量（操作完反馈页也能及时更新）
watch(
  () => route.path,
  () => refreshPendingFeedback(),
)

const TITLES = {
  'admin-dashboard': '数据概览',
  'admin-reservations': '就餐预约',
  'admin-menus': '菜单管理',
  'admin-feedback': '意见反馈',
  'admin-reviews': '菜品评价',
  'admin-votes': '最爱菜投票',
  'admin-users': '员工管理',
  'admin-settings': '系统设置',
}

const pageTitle = computed(() => TITLES[route.name] || '管理后台')

const tabs = ref([{ path: '/admin', title: '数据概览' }])
watch(
  () => route.path,
  (path) => {
    if (!tabs.value.some((tab) => tab.path === path)) {
      tabs.value.push({ path, title: pageTitle.value })
    }
  },
  { immediate: true },
)

function closeTab(tab) {
  if (tab.path === '/admin') return
  const index = tabs.value.findIndex((entry) => entry.path === tab.path)
  tabs.value = tabs.value.filter((entry) => entry.path !== tab.path)
  if (route.path === tab.path) {
    const next = tabs.value[Math.min(index, tabs.value.length - 1)]
    router.push(next ? next.path : '/admin')
  }
}

const userOptions = [{ label: '退出登录', key: 'logout' }]

function initial(name) {
  return (name || '').trim().slice(-1) || '管'
}

async function onUserAction(key) {
  if (key === 'logout') {
    await adminLogout()
    router.replace('/admin/login')
  }
}
</script>

<template>
  <n-config-provider :theme-overrides="themeOverrides" :locale="zhCN" :date-locale="dateZhCN" class="admin-app">
    <n-dialog-provider>
      <n-message-provider>
        <n-layout has-sider class="shell">
          <n-layout-sider
            collapse-mode="width"
            :collapsed="collapsed"
            :collapsed-width="64"
            :width="228"
            :native-scrollbar="false"
            class="sider"
          >
            <RouterLink to="/admin" class="logo" :class="{ collapsed }">
              <span class="logo-mark">
                <svg viewBox="0 0 48 48" width="18" height="18" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M8 22h32c0 9.4-7.2 16-16 16S8 31.4 8 22Z" />
                  <path d="M18 15c0-2.5 2-3.5 2-5.5M26 15c0-2.5 2-3.5 2-5.5" />
                </svg>
              </span>
              <span v-if="!collapsed" class="logo-text">
                <strong>博涯小食堂</strong>
                <i>CANTEEN ADMIN</i>
              </span>
            </RouterLink>

            <n-menu
              :value="route.path"
              :options="menuOptions"
              :collapsed="collapsed"
              :collapsed-width="64"
              :collapsed-icon-size="19"
              :indent="16"
              class="menu"
            />

            <!--
              收起/展开导航：单独用一个小 n-menu 渲染，
              这样和上面的菜单项共用同一套高度、缩进、hover 与收起居中规则，
              不会再出现「按钮和图标不协调」的问题。
            -->
            <n-menu
              :value="null"
              :options="collapseOptions"
              :collapsed="collapsed"
              :collapsed-width="64"
              :collapsed-icon-size="19"
              :indent="16"
              class="menu menu-footer"
              @update:value="onMenuSelect"
            />
          </n-layout-sider>

          <n-layout class="main">
            <header class="topbar">
              <div class="crumb">
                <span>管理后台</span>
                <i>/</i>
                <strong>{{ pageTitle }}</strong>
              </div>
              <div class="topbar-right">
                <button class="icon-btn" title="刷新当前页" @click="refreshKey += 1">
                  <n-icon :size="16"><RefreshOutline /></n-icon>
                </button>
                <n-dropdown :options="userOptions" trigger="click" @select="onUserAction">
                  <button class="user" type="button">
                    <span class="avatar">{{ initial(store.admin?.name) }}</span>
                    <span class="user-meta">
                      <strong>{{ store.admin?.name || '管理员' }}</strong>
                      <i>{{ roleLabel(store.admin?.role) }}</i>
                    </span>
                  </button>
                </n-dropdown>
              </div>
            </header>

            <div v-if="tabs.length > 1" class="tabs">
              <button
                v-for="tab in tabs"
                :key="tab.path"
                class="tab"
                :class="{ active: route.path === tab.path }"
                type="button"
                @click="router.push(tab.path)"
              >
                {{ tab.title }}
                <i v-if="tab.path !== '/admin'" class="tab-close" @click.stop="closeTab(tab)">
                  <n-icon :size="11"><CloseOutline /></n-icon>
                </i>
              </button>
            </div>

            <n-layout-content class="content">
              <router-view :key="route.path + refreshKey" />
            </n-layout-content>
          </n-layout>
        </n-layout>
      </n-message-provider>
    </n-dialog-provider>
  </n-config-provider>
</template>

<style scoped>
.shell {
  min-height: 100vh;
  background: #f7f8fa;
  color: #111827;
}

/* ── 纯白侧栏 ───────────────────────────── */
.sider {
  background: #ffffff !important;
  border-right: 1px solid #eceef2;
}

.sider :deep(.n-layout-sider-scroll-container) {
  display: flex;
  flex-direction: column;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 18px 16px 16px;
  text-decoration: none;
}

/* 收起时 logo 方块居中：宽度 64，方块 32，两侧各 16 */
.logo.collapsed {
  justify-content: center;
  padding: 18px 0 16px;
}

.logo.collapsed .logo-mark {
  margin: 0 auto;
}

.logo-mark {
  width: 32px;
  height: 32px;
  border-radius: 9px;
  background: #111827;
  display: grid;
  place-items: center;
  flex: none;
}

.logo-text {
  display: flex;
  flex-direction: column;
  line-height: 1.3;
  min-width: 0;
}

.logo-text strong {
  color: #111827;
  font-size: 14.5px;
  letter-spacing: 0.5px;
  white-space: nowrap;
}

.logo-text i {
  color: #a3abb8;
  font-size: 9.5px;
  font-style: normal;
  letter-spacing: 1.6px;
}

.menu {
  padding: 2px 10px 12px;
  flex: 1;
}

/* 底部收起/展开项：与上方菜单同宽同缩进，只加一条淡淡的分割线 */
.menu-footer {
  flex: none;
  padding-top: 10px;
  border-top: 1px solid #f1f3f6;
}

/* 收起导航：让图标在 44px 宽的内容区里居中（与其它菜单项同一套规则） */
.menu :deep(.n-menu--collapsed .n-menu-item-content) {
  display: flex;
  align-items: center;
  justify-content: center;
  padding-left: 0 !important;
  padding-right: 0 !important;
}

.menu :deep(.n-menu--collapsed .n-menu-item-content-header) {
  display: none;
}

.menu :deep(.n-menu--collapsed .n-menu-item-content .menu-ico) {
  justify-content: center;
}

/* 菜单文字：常态深灰、选中近黑，保证白底上的可读性 */
.menu :deep(.n-menu-item-content) {
  color: #3d4652;
  font-weight: 500;
  border-radius: 8px;
}

.menu :deep(.n-menu-item-content .n-menu-item-content-header) {
  font-size: 13.5px;
}

.menu :deep(.n-menu-item-content:hover) {
  color: #111827;
  background: #f4f5f7;
}

.menu :deep(.n-menu-item-content--selected) {
  color: #0f172a;
  background: #eef1f5;
  font-weight: 600;
}

.menu :deep(.n-menu-item-content--selected::before) {
  display: none;
}

.menu :deep(.n-menu-item-content--selected .n-icon) {
  color: #0f172a;
}

.menu :deep(.n-menu-item-group-title) {
  color: #9aa3af;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 1.2px;
  padding: 14px 14px 6px;
  text-transform: none;
}

/* 待处理反馈小红点 */
.menu :deep(.nav-dot) {
  display: inline-block;
  width: 6px;
  height: 6px;
  margin-left: 6px;
  border-radius: 50%;
  background: #e5484d;
  vertical-align: 2px;
}

/* 图标统一包一层，保证所有菜单项（含收起/展开）图标同一尺寸同一圆心 */
.menu :deep(.menu-ico) {
  position: relative;
  width: 22px;
  height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: none;
}

.menu :deep(.nav-ico-dot) {
  position: absolute;
  top: -3px;
  right: -3px;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #e5484d;
  box-shadow: 0 0 0 2px #fff;
}

/* ── 顶栏 ──────────────────────────────── */
.main {
  background: #f7f8fa;
}

.topbar {
  height: 54px;
  background: #ffffff;
  border-bottom: 1px solid #eceef2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  position: sticky;
  top: 0;
  z-index: 20;
}

.crumb {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #97a0ad;
}

.crumb i {
  color: #d3d8e0;
  font-style: normal;
}

.crumb strong {
  color: #111827;
  font-weight: 600;
  font-size: 13.5px;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 6px;
}

.icon-btn {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #8b95a3;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: 0.15s;
}

.icon-btn:hover {
  background: #f4f5f7;
  color: #111827;
}

.user {
  display: flex;
  align-items: center;
  gap: 9px;
  border: none;
  background: transparent;
  cursor: pointer;
  padding: 4px 8px 4px 4px;
  border-radius: 10px;
  transition: 0.15s;
}

.user:hover {
  background: #f4f5f7;
}

.avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: #eef1f5;
  color: #333c49;
  font-size: 12.5px;
  font-weight: 600;
  display: grid;
  place-items: center;
}

.user-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  line-height: 1.25;
}

.user-meta strong {
  color: #111827;
  font-size: 12.5px;
  font-weight: 600;
}

.user-meta i {
  color: #9aa3af;
  font-size: 10.5px;
  font-style: normal;
}

/* ── 标签页 ────────────────────────────── */
.tabs {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 16px 0;
  background: #ffffff;
  border-bottom: 1px solid #eceef2;
  overflow-x: auto;
}

.tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 30px;
  padding: 0 11px;
  border: none;
  border-bottom: 2px solid transparent;
  background: transparent;
  color: #8b95a3;
  font-size: 12.5px;
  cursor: pointer;
  white-space: nowrap;
  transition: 0.15s;
}

.tab:hover {
  color: #3d4652;
}

.tab.active {
  color: #111827;
  font-weight: 600;
  border-bottom-color: #111827;
}

.tab-close {
  display: inline-flex;
  border-radius: 4px;
  padding: 1px;
  color: #a8b1bd;
}

.tab-close:hover {
  background: #eceef2;
  color: #111827;
}

.content {
  padding: 18px 20px 28px;
  background: #f7f8fa;
}
</style>
