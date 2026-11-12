<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'

const route = useRoute()
const router = useRouter()

const tabs = [
  { path: '/', name: 'home', label: '首页', icon: 'home' },
  { path: '/menu', name: 'menu', label: '菜单', icon: 'menu' },
  { path: '/review', name: 'review', label: '评价', icon: 'star' },
  { path: '/me', name: 'me', label: '我的', icon: 'user' },
]

// 用 path 前缀判断，子页面（如 /feedback）也能正确高亮
const activePath = computed(() => {
  const path = route.path
  if (path === '/') return '/'
  const hit = tabs.find((tab) => tab.path !== '/' && path.startsWith(tab.path))
  return hit ? hit.path : '/'
})

function go(tab) {
  if (activePath.value === tab.path && route.path === tab.path) return
  router.push(tab.path)
}
</script>

<template>
  <div class="shell">
    <div class="viewport">
      <router-view v-slot="{ Component, route: current }">
        <div :key="current.path" class="page-anim">
          <component :is="Component" />
        </div>
      </router-view>
    </div>

    <nav class="tabbar">
      <button
        v-for="tab in tabs"
        :key="tab.path"
        type="button"
        class="tab"
        :class="{ active: activePath === tab.path }"
        @click="go(tab)"
      >
        <span class="tab-icon">
          <AppIcon :name="tab.icon" :size="22" :stroke-width="activePath === tab.path ? 2.1 : 1.7" />
        </span>
        <span class="tab-label">{{ tab.label }}</span>
      </button>
    </nav>
  </div>
</template>

<style scoped>
.shell {
  min-height: 100%;
  background: var(--bg);
}

.viewport {
  min-height: 100%;
}

.tabbar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 30;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  align-items: center;
  height: calc(58px + env(safe-area-inset-bottom));
  padding-bottom: env(safe-area-inset-bottom);
  background: var(--veil);
  border-top: 1px solid var(--line);
  backdrop-filter: blur(14px);
  box-shadow: 0 -8px 24px rgba(16, 43, 66, 0.06);
}

.tab {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  height: 100%;
  padding: 7px 0 4px;
  border: none;
  background: transparent;
  color: var(--text-3);
  font-family: inherit;
  transition: color 0.18s ease;
}

.tab-icon {
  display: grid;
  place-items: center;
  width: 34px;
  height: 26px;
  border-radius: 999px;
  transition: background 0.2s ease, transform 0.2s ease;
}

.tab-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.2px;
}

.tab.active {
  color: var(--brand-deep);
}

html[data-theme='dark'] .tab.active {
  color: #7cd8fb;
}

.tab.active .tab-icon {
  background: var(--brand-soft);
  transform: translateY(-1px);
}

.tab:active .tab-icon {
  transform: scale(0.92);
}
</style>
