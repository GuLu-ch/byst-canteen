<script setup>
import { computed, onMounted, ref } from 'vue'
import { showToast } from 'vant'
import { useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import { api } from '../api/client'
import { store } from '../stores/app'
import { isDark, toggleTheme } from '../utils/theme'
import { MEAL_LABELS, addDays, monthDay, todayISO, weekdayLabel } from '../utils/date'

const router = useRouter()
const MEALS = ['breakfast', 'lunch', 'dinner']
const MEAL_ICONS = { breakfast: 'sparkles', lunch: 'bowl', dinner: 'utensils' }
const TYPE_CLASS = { 荤菜: 'meat', 素菜: 'veg', 汤品: 'soup', 主食: 'staple', 凉菜: 'cold', 小菜: 'side' }

const today = todayISO()
const tomorrow = addDays(today, 1)

const canteen = computed(() => store.settings?.canteen_name || '博涯小食堂')
const announcement = computed(() => store.settings?.announcement || '')

/* ---------------- 明日三餐 ---------------- */
const tomorrowMenu = ref(null)
const tomorrowAvail = ref(null)
const tomorrowMine = ref([])

const tomorrowMeals = computed(() =>
  MEALS.map((meal) => ({
    meal,
    label: MEAL_LABELS[meal],
    menu: tomorrowMenu.value?.meals?.[meal] || null,
    state: tomorrowAvail.value?.[meal] || null,
    reserved: tomorrowMine.value.includes(meal),
  })),
)

const tomorrowPicked = computed(() => tomorrowMeals.value.filter((item) => item.reserved).length)

async function loadTomorrow() {
  try {
    const [menu, av, mine] = await Promise.all([
      api.get(`/menus/day/${tomorrow}`),
      api.get('/reservations/availability', { start: tomorrow, end: tomorrow }),
      api.get('/reservations/mine', { start: tomorrow, end: tomorrow }),
    ])
    tomorrowMenu.value = menu
    tomorrowAvail.value = av.days?.[0]?.meals || null
    tomorrowMine.value = (mine.items || []).map((item) => item.meal)
  } catch (error) {
    showToast(error.message || '菜单加载失败')
  }
}

/* ---------------- 投票入口数据（详情在 /vote 页） ---------------- */
const voterCount = ref(0)

async function loadVoteSummary() {
  try {
    const data = await api.get('/votes/results')
    voterCount.value = data.total_votes ?? 0
  } catch {
    /* 首页入口的次要数据，失败不打扰 */
  }
}

onMounted(() => {
  loadTomorrow()
  loadVoteSummary()
})
</script>

<template>
  <div class="home">
    <header class="hero">
      <div class="hero-row">
        <div class="hero-title">
          <h1 class="canteen">{{ canteen }}</h1>
          <span class="date-chip">
            <AppIcon name="calendar" :size="14" />
            {{ monthDay(today) }} {{ weekdayLabel(today) }}
          </span>
        </div>
        <div class="hero-actions">
          <button type="button" class="hero-btn" :title="isDark ? '切换浅色' : '切换深色'" @click="toggleTheme">
            <AppIcon :name="isDark ? 'sun' : 'moon'" :size="18" />
          </button>
        </div>
      </div>

      <p v-if="announcement" class="notice">
        <AppIcon name="bell" :size="14" />
        <span>{{ announcement }}</span>
      </p>
    </header>

    <div class="page">
      <section class="card tomorrow-card">
        <div class="card-head">
          <div class="card-title">
            <h3>明日三餐</h3>
            <span class="muted small">{{ monthDay(tomorrow) }} {{ weekdayLabel(tomorrow) }}</span>
          </div>
          <span class="pick-pill" :class="{ on: tomorrowPicked }">
            {{ tomorrowPicked ? `已约 ${tomorrowPicked}/3` : '未预约' }}
          </span>
          <button type="button" class="head-link" @click="router.push('/menu')">
            本周菜单
            <AppIcon name="chevron-right" :size="13" />
          </button>
        </div>

        <div class="meal-list">
          <button
            v-for="item in tomorrowMeals"
            :key="item.meal"
            type="button"
            class="meal-row"
            :class="{ picked: item.reserved }"
            @click="router.push('/menu')"
          >
            <span class="meal-ico" :class="item.meal">
              <AppIcon :name="MEAL_ICONS[item.meal]" :size="17" />
            </span>
            <span class="meal-body">
              <span class="meal-title">
                {{ item.label }}
                <i v-if="item.reserved" class="tick"><AppIcon name="check" :size="11" :stroke-width="3" /></i>
              </span>
              <span class="meal-dishes">
                <template v-if="item.menu?.dishes?.length">
                  <span v-for="dish in item.menu.dishes" :key="dish.name" class="dish">
                    {{ dish.name }}<i class="type" :class="TYPE_CLASS[dish.type] || 'side'">{{ dish.type }}</i>
                  </span>
                </template>
                <span v-else class="muted">菜单待上传</span>
              </span>
            </span>
            <span class="chev"><AppIcon name="chevron-right" :size="16" /></span>
          </button>
        </div>

        <button type="button" class="primary-btn full" @click="router.push('/menu')">
          去预约本周剩下的餐
          <AppIcon name="chevron-right" :size="16" />
        </button>
      </section>

      <button type="button" class="feedback-entry" @click="router.push('/vote')">
        <span class="fe-ico vote">
          <AppIcon name="heart" :size="18" />
        </span>
        <span class="fe-body">
          <b>本周最爱菜投票</b>
          <span class="muted small">可多选 · {{ voterCount }} 人已投</span>
        </span>
        <span class="chev"><AppIcon name="chevron-right" :size="16" /></span>
      </button>

      <button type="button" class="feedback-entry" @click="router.push('/feedback')">
        <span class="fe-ico">
          <AppIcon name="message" :size="18" />
        </span>
        <span class="fe-body">
          <b>食堂意见反馈</b>
          <span class="muted small">口味咸淡 · 卫生餐具 · 完全匿名</span>
        </span>
        <span class="chev"><AppIcon name="chevron-right" :size="16" /></span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.home {
  padding-bottom: calc(88px + env(safe-area-inset-bottom));
}

.hero {
  padding: 14px 16px 40px;
  background: var(--grad-hero);
  border-radius: 0 0 26px 26px;
  color: var(--hero-text);
  box-shadow: 0 14px 30px rgba(3, 105, 161, 0.28);
}

.hero-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.canteen {
  font-size: 21px;
  font-weight: 800;
  letter-spacing: 0.4px;
}

.hero-title {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.hero-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: none;
}

.hero-btn {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border: 1px solid var(--hero-veil-line);
  border-radius: 12px;
  background: var(--hero-veil);
  color: var(--hero-text);
  font-family: inherit;
  transition: transform 0.18s ease, background 0.18s ease;
}

.hero-btn:active {
  transform: scale(0.92);
}

.date-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 10px;
  border-radius: 999px;
  background: var(--hero-veil);
  border: 1px solid var(--hero-veil-line);
  font-size: 12px;
  font-weight: 600;
  color: var(--hero-text);
  white-space: nowrap;
  flex: none;
}

.notice {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-top: 12px;
  padding: 9px 11px;
  border-radius: 12px;
  background: var(--hero-veil);
  border: 1px solid var(--hero-veil-line);
  font-size: 12px;
  line-height: 1.5;
  color: var(--hero-text);
}

.feedback-entry {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  margin-top: 12px;
  padding: 14px 16px;
  border-radius: var(--radius-lg);
  background: var(--card);
  border: 1px solid var(--line);
  box-shadow: var(--shadow);
  font-family: inherit;
  text-align: left;
  transition: transform 0.18s ease;
}

.feedback-entry:active {
  transform: scale(0.985);
}

.fe-ico {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  flex: none;
  border-radius: 13px;
  background: var(--brand-soft);
  color: var(--brand);
}

.fe-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.fe-ico.vote {
  background: rgba(240, 68, 56, 0.1);
  color: #f04438;
}

.fe-body b {
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
}

.page {
  margin-top: -26px;
  padding: 0 16px calc(40px + env(safe-area-inset-bottom));
}

.card,
.tomorrow-card {
  padding: 14px;
  margin-bottom: 12px;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow);
}

/* 卡内头部行：标题 + 状态 + 链接按钮在一行，不再悬空 */
.card-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.card-title {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.card-title h3 {
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
}

.card-title .small {
  font-size: 11px;
}

.pick-pill {
  flex: none;
  padding: 3px 9px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  background: var(--card-2);
  color: var(--text-3);
}

.pick-pill.on {
  background: var(--brand-soft);
  color: var(--brand-dark);
}

.head-link {
  flex: none;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 6px 12px;
  border: none;
  border-radius: 999px;
  background: var(--brand-soft);
  color: var(--brand-dark);
  font-size: 12px;
  font-weight: 600;
  font-family: inherit;
  transition: transform 0.18s ease;
}

html[data-theme='dark'] .head-link {
  color: #7cd8fb;
}

.head-link:active {
  transform: scale(0.96);
}

.small {
  font-size: 12px;
}

.meal-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.meal-row {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--card-2);
  text-align: left;
  font-family: inherit;
  transition: border-color 0.18s ease, background 0.18s ease, transform 0.18s ease;
}

.meal-row:active {
  transform: scale(0.99);
}

.meal-row.picked {
  border-color: rgba(5, 175, 240, 0.45);
  background: var(--brand-softer);
}

.meal-ico {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 11px;
  background: var(--brand-soft);
  color: var(--brand-deep);
  flex: none;
}

.meal-ico.lunch {
  background: #e8f8ef;
  color: #0d8a4f;
}

.meal-ico.dinner {
  background: #eef0ff;
  color: #5a5cd6;
}

html[data-theme='dark'] .meal-ico.lunch {
  background: rgba(23, 178, 106, 0.16);
  color: #4ade8f;
}

html[data-theme='dark'] .meal-ico.dinner {
  background: rgba(122, 90, 248, 0.18);
  color: #a79bff;
}

.meal-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  flex: 1;
}

.meal-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
}

.tick {
  display: grid;
  place-items: center;
  width: 15px;
  height: 15px;
  border-radius: 50%;
  background: var(--brand);
  color: #fff;
}

.meal-dishes {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 6px;
  font-size: 12px;
  color: var(--text-2);
}

.dish {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.dish .type {
  font-style: normal;
  font-size: 10px;
  padding: 0 4px;
  border-radius: 5px;
  background: var(--card);
  color: var(--text-3);
}

html[data-theme='dark'] .dish .type {
  background: rgba(255, 255, 255, 0.06);
}

.dish .type.meat {
  color: #e0564a;
  background: rgba(240, 68, 56, 0.12);
}

.dish .type.veg {
  color: #17b26a;
  background: rgba(23, 178, 106, 0.13);
}

.dish .type.soup {
  color: #e08a1d;
  background: rgba(247, 144, 9, 0.13);
}

.dish .type.staple {
  color: #7a7ff0;
  background: rgba(122, 90, 248, 0.13);
}

.dish .type.cold {
  color: #12a3d6;
  background: rgba(5, 175, 240, 0.12);
}

.chev {
  color: var(--text-3);
  flex: none;
}

.full {
  width: 100%;
  margin-top: 12px;
}

</style>
