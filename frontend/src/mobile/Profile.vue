<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showConfirmDialog, showToast } from 'vant'
import AppIcon from '../components/AppIcon.vue'
import { api } from '../api/client'
import { isDark, logout, roleLabel, store, toggleTheme } from '../stores/app'
import { MEAL_LABELS, addDays, monthDay, todayISO, weekdayLabel } from '../utils/date'

const router = useRouter()

const user = computed(() => store.user)
const initial = computed(() => (user.value?.name || '员').slice(-1))

const stats = ref({})
const upcoming = ref([])
const showProfile = ref(false)
const showPassword = ref(false)
const saving = ref(false)
const changing = ref(false)

const form = reactive({ name: '', allergens: '', preferences: '', taste: '', favorite_dishes: '' })
const pwd = reactive({ old: '', next: '', confirm: '' })

const maskPhone = (phone) => (!phone || phone.length < 7 ? phone || '' : `${phone.slice(0, 3)}****${phone.slice(-4)}`)

const entries = computed(() => {
  const list = [
    {
      label: isDark.value ? '切换浅色模式' : '切换深色模式',
      desc: '深浅主题随时切换，自动记住选择',
      icon: isDark.value ? 'sun' : 'moon',
      action: () => toggleTheme(),
    },
    { label: '意见反馈', desc: '匿名提交，厨师和管理员都看不到是谁', icon: 'message', action: () => router.push('/feedback') },
    { label: '修改密码', desc: '定期更换更安全', icon: 'lock', action: () => (showPassword.value = true) },
  ]
  return list
})

function openProfile() {
  Object.assign(form, {
    name: user.value?.name || '',
    allergens: user.value?.allergens || '',
    preferences: user.value?.preferences || '',
    taste: user.value?.taste || '',
    favorite_dishes: user.value?.favorite_dishes || '',
  })
  showProfile.value = true
}

async function load() {
  const from = todayISO()
  const [meStats, mine] = await Promise.all([
    api.get('/stats/me'),
    api.get('/reservations/mine', { start: from, end: addDays(from, 30) }),
  ])
  stats.value = meStats || {}
  const items = (mine.items || []).filter((item) => item.status === 'reserved')
  items.sort((a, b) => (a.date + a.meal).localeCompare(b.date + b.meal))
  upcoming.value = items.slice(0, 5)
}

async function saveProfile() {
  if (!form.name.trim()) {
    showToast('姓名不能为空')
    return
  }
  saving.value = true
  try {
    store.user = await api.put('/auth/profile', {
      name: form.name.trim(),
      allergens: form.allergens.trim(),
      preferences: form.preferences.trim(),
      taste: form.taste.trim(),
      favorite_dishes: form.favorite_dishes.trim(),
    })
    showToast('资料已更新')
    showProfile.value = false
  } catch (error) {
    showToast(error.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function changePassword() {
  if (pwd.next.length < 6) {
    showToast('新密码至少 6 位')
    return
  }
  if (pwd.next !== pwd.confirm) {
    showToast('两次输入的新密码不一致')
    return
  }
  changing.value = true
  try {
    await api.post('/auth/password', { old_password: pwd.old, new_password: pwd.next })
    showToast('密码修改成功')
    showPassword.value = false
    pwd.old = ''
    pwd.next = ''
    pwd.confirm = ''
  } catch (error) {
    showToast(error.message || '修改失败')
  } finally {
    changing.value = false
  }
}

async function handleLogout() {
  try {
    await showConfirmDialog({ title: '退出登录', message: '确定要退出当前账号吗？' })
    logout()
    router.replace('/login')
  } catch {
    /* 用户取消 */
  }
}

onMounted(() => {
  load().catch(() => {})
})
</script>

<template>
  <div class="me-page">
    <header class="hero">
      <div class="hero-top">
        <div class="avatar">{{ initial }}</div>
        <div class="who">
          <p class="name">{{ user?.name || '未登录' }}</p>
          <p class="meta">
            <span class="role">{{ roleLabel(user?.role) }}</span>
            <span>{{ maskPhone(user?.phone) }}</span>
            <span v-if="user?.department">{{ user.department }}</span>
          </p>
        </div>
        <button type="button" class="edit" @click="openProfile">
          <AppIcon name="edit" :size="14" />
          编辑
        </button>
      </div>

      <div class="metrics">
        <div class="metric">
          <b>{{ stats.upcoming_count ?? 0 }}</b>
          <span>待就餐</span>
        </div>
        <div class="metric">
          <b>{{ stats.review_count ?? 0 }}</b>
          <span>评价</span>
        </div>
        <div class="metric">
          <b>{{ stats.vote_count ?? 0 }}</b>
          <span>投票</span>
        </div>
        <div class="metric">
          <b>{{ stats.feedback_count ?? 0 }}</b>
          <span>反馈</span>
        </div>
      </div>
    </header>

    <div class="page">
      <section class="card prefs">
        <div class="section-head">
          <h3>我的口味档案</h3>
          <button type="button" class="link" @click="openProfile">
            修改
            <AppIcon name="chevron-right" :size="14" />
          </button>
        </div>
        <div class="pref-row">
          <span class="pref-key">忌口</span>
          <span class="pref-val" :class="{ empty: !user?.allergens }">{{ user?.allergens || '未填写' }}</span>
        </div>
        <div class="pref-row">
          <span class="pref-key">偏好</span>
          <span class="pref-val" :class="{ empty: !user?.preferences }">{{ user?.preferences || '未填写' }}</span>
        </div>
        <div class="pref-row">
          <span class="pref-key">口味</span>
          <span class="pref-val" :class="{ empty: !user?.taste }">{{ user?.taste || '未填写' }}</span>
        </div>
        <div class="pref-row">
          <span class="pref-key">喜欢的菜</span>
          <span class="pref-val" :class="{ empty: !user?.favorite_dishes }">{{ user?.favorite_dishes || '未填写' }}</span>
        </div>
      </section>

      <section class="card reservations">
        <div class="section-head">
          <h3>我的预约</h3>
          <button type="button" class="link" @click="router.push('/menu')">
            去预约
            <AppIcon name="chevron-right" :size="14" />
          </button>
        </div>
        <div v-if="!upcoming.length" class="empty">
          <AppIcon name="calendar" :size="26" />
          <span>还没有待就餐的预约</span>
        </div>
        <div v-for="item in upcoming" :key="item.id" class="res-row">
          <span class="res-date">
            {{ item.date }}
            <i>{{ weekdayLabel(item.date) }}</i>
          </span>
          <span class="res-meal">{{ MEAL_LABELS[item.meal] }}</span>
          <span class="pill green">已预约</span>
        </div>
      </section>

      <section class="card entries">
        <button v-for="entry in entries" :key="entry.label" type="button" class="entry" @click="entry.action()">
          <span class="entry-ico"><AppIcon :name="entry.icon" :size="18" /></span>
          <span class="entry-body">
            <span class="entry-label">{{ entry.label }}</span>
            <span class="entry-desc">{{ entry.desc }}</span>
          </span>
          <AppIcon name="chevron-right" :size="16" class="entry-arrow" />
        </button>
      </section>

      <button type="button" class="logout" @click="handleLogout">
        <AppIcon name="logout" :size="16" />
        退出登录
      </button>
    </div>

    <!-- 编辑资料：sheet 骨架，标题吸顶、表单区内部滚动，不再溢出 -->
    <van-popup teleport="body" v-model:show="showProfile" round position="bottom" :style="{ height: '80vh' }">
      <div class="sheet">
        <div class="sheet-head">
          <h3>编辑我的资料</h3>
          <span class="spacer" />
          <button type="button" class="close" @click="showProfile = false">
            <AppIcon name="close" :size="18" />
          </button>
        </div>
        <div class="sheet-body">
          <label class="field">
            <span>姓名</span>
            <input v-model="form.name" maxlength="20" placeholder="你的名字" />
          </label>
          <label class="field">
            <span>忌口 / 过敏</span>
            <textarea v-model="form.allergens" rows="2" maxlength="100" placeholder="例如：不吃香菜、海鲜过敏" />
          </label>
          <label class="field">
            <span>饮食偏好</span>
            <textarea v-model="form.preferences" rows="2" maxlength="100" placeholder="例如：爱吃辣、喜欢清淡" />
          </label>
          <label class="field">
            <span>口味</span>
            <textarea v-model="form.taste" rows="2" maxlength="100" placeholder="例如：少油少盐、不要太咸" />
          </label>
          <label class="field">
            <span>喜欢的菜</span>
            <textarea v-model="form.favorite_dishes" rows="2" maxlength="100" placeholder="例如：红烧肉、番茄炒蛋" />
          </label>
        </div>
        <button type="button" class="primary-btn full" :disabled="saving" @click="saveProfile">
          {{ saving ? '保存中…' : '保存' }}
        </button>
      </div>
    </van-popup>

    <van-popup teleport="body" v-model:show="showPassword" round position="bottom" :style="{ height: '64vh' }">
      <div class="sheet">
        <div class="sheet-head">
          <h3>修改密码</h3>
          <span class="spacer" />
          <button type="button" class="close" @click="showPassword = false">
            <AppIcon name="close" :size="18" />
          </button>
        </div>
        <div class="sheet-body">
          <label class="field">
            <span>原密码</span>
            <input v-model="pwd.old" type="password" maxlength="32" placeholder="当前密码" />
          </label>
          <label class="field">
            <span>新密码</span>
            <input v-model="pwd.next" type="password" maxlength="32" placeholder="至少 6 位" />
          </label>
          <label class="field">
            <span>确认新密码</span>
            <input v-model="pwd.confirm" type="password" maxlength="32" placeholder="再输入一次" />
          </label>
        </div>
        <button type="button" class="primary-btn full" :disabled="changing" @click="changePassword">
          {{ changing ? '提交中…' : '确认修改' }}
        </button>
      </div>
    </van-popup>
  </div>
</template>

<style scoped>
.me-page {
  padding-bottom: calc(70px + env(safe-area-inset-bottom));
}

.hero {
  padding: 22px 16px 46px;
  background: var(--grad-hero);
  border-radius: 0 0 26px 26px;
  color: var(--hero-text);
  box-shadow: var(--shadow-brand);
}

.hero-top {
  display: flex;
  align-items: center;
  gap: 12px;
}

.avatar {
  display: grid;
  place-items: center;
  width: 52px;
  height: 52px;
  border-radius: 18px;
  background: var(--hero-veil);
  border: 1px solid var(--hero-veil-line);
  font-size: 20px;
  font-weight: 700;
}

.who {
  flex: 1;
  min-width: 0;
}

.name {
  font-size: 18px;
  font-weight: 700;
}

.meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 5px;
  font-size: 11px;
  color: var(--hero-text-2);
  flex-wrap: wrap;
}

.role {
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--hero-veil);
  border: 1px solid var(--hero-veil-line);
  font-weight: 600;
}

.edit {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 7px 11px;
  border: 1px solid var(--hero-veil-line);
  border-radius: 999px;
  background: var(--hero-veil);
  color: var(--hero-text);
  font-size: 12px;
  font-weight: 600;
  font-family: inherit;
}

.metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-top: 18px;
  padding: 12px 6px;
  border-radius: 16px;
  background: var(--hero-veil);
  border: 1px solid var(--hero-veil-line);
}

.metric {
  text-align: center;
}

.metric b {
  display: block;
  font-size: 18px;
  font-weight: 800;
}

.metric span {
  font-size: 10px;
  color: var(--hero-text-2);
}

.page {
  margin-top: -30px;
  padding: 0 16px 0;
}

.card {
  padding: 14px;
  margin-bottom: 12px;
}

.pref-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 9px 0;
  border-bottom: 1px solid var(--line);
}

.pref-row:last-child {
  border-bottom: none;
}

.pref-key {
  width: 58px;
  flex: none;
  font-size: 12px;
  color: var(--text-3);
}

.pref-val {
  font-size: 13px;
  line-height: 1.55;
  color: var(--text);
}

.pref-val.empty {
  color: var(--text-3);
}

.res-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid var(--line);
  font-size: 13px;
}

.res-row:last-child {
  border-bottom: none;
}

.res-date {
  width: 74px;
  font-weight: 700;
  color: var(--text);
}

.res-date i {
  margin-left: 4px;
  font-style: normal;
  font-size: 11px;
  font-weight: 500;
  color: var(--text-3);
}

.res-meal {
  flex: 1;
  color: var(--text-2);
}

.entries {
  padding: 4px 14px;
}

.entry {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 13px 0;
  border: none;
  border-bottom: 1px solid var(--line);
  background: none;
  font-family: inherit;
  text-align: left;
}

.entry:last-child {
  border-bottom: none;
}

.entry-ico {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 12px;
  background: var(--brand-soft);
  color: var(--brand-deep);
  flex: none;
}

.entry-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.entry-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}

.entry-desc {
  font-size: 11px;
  color: var(--text-3);
}

.entry-arrow {
  color: var(--text-3);
  flex: none;
}

.logout {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  margin-top: 4px;
  padding: 13px;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: var(--card);
  color: var(--danger);
  font-size: 14px;
  font-weight: 600;
  font-family: inherit;
}

/* 表单字段在弹层内的样式：吸顶标题下的内容区自己滚动 */
.field {
  display: block;
  margin-bottom: 12px;
}

.field span {
  display: block;
  margin-bottom: 6px;
  font-size: 12px;
  color: var(--text-2);
}

.field input,
.field textarea {
  width: 100%;
  padding: 11px 12px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--card-2);
  color: var(--text);
  font-size: 13px;
  font-family: inherit;
  resize: none;
  outline: none;
}

.field input:focus,
.field textarea:focus {
  border-color: var(--brand);
  background: var(--card);
}

.full {
  width: 100%;
  margin-top: 6px;
}
</style>
