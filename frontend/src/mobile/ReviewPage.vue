<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import AppIcon from '../components/AppIcon.vue'
import { api } from '../api/client'
import { addDays, MEALS, MEAL_LABELS, formatDateTime, fullDateLabel, todayISO, weekdayLabel } from '../utils/date'

const ratingList = [
  { value: 5, label: '非常好', emoji: '😍' },
  { value: 4, label: '很好', emoji: '😋' },
  { value: 3, label: '良好', emoji: '🙂' },
  { value: 2, label: '一般', emoji: '😕' },
  { value: 1, label: '很差', emoji: '😣' },
]

const tasteOptions = ['太咸', '太淡', '刚好', '太辣', '不够辣', '太软', '太硬', '不熟', '其他']
const pairingOptions = ['荤菜太少', '素菜太少', '种类重复', '搭配不合理']
const portionOptions = ['太少', '太多', '刚好']

const route = useRoute()
const router = useRouter()

const today = todayISO()
const minDay = addDays(today, -29)

/* 当前正在评价的餐次（早/中/晚独立） */
const day = ref(today)
const meal = ref('lunch')
const meals = MEALS

/* 每个餐次独立的表单状态：{ breakfast: {rating,taste,...,existing}, ... } */
function blankForm() {
  return { rating: 0, taste: '', pairing: '', portion: '', comment: '', existing: null }
}
const forms = ref({ breakfast: blankForm(), lunch: blankForm(), dinner: blankForm() })
const menus = ref({ breakfast: null, lunch: null, dinner: null })

const history = ref([])
const showHistory = ref(false)
const submitting = ref(false)
const loading = ref(true)

const current = computed(() => forms.value[meal.value])
const needReason = computed(() => current.value.rating > 0 && current.value.rating <= 2)
const ratedCount = computed(() => Object.values(forms.value).filter((form) => form.existing).length)
const recentHistory = computed(() => history.value.slice(0, 3))
const ratingLabel = (value) => ratingList.find((item) => item.value === value)?.label || ''
const reasonsText = (item) => [item.taste, item.pairing, item.portion].filter(Boolean).join(' · ')

function pickRating(value) {
  const form = current.value
  form.rating = value
  if (value >= 3) {
    form.taste = ''
    form.pairing = ''
    form.portion = ''
  }
}

function shiftDay(step) {
  const next = addDays(day.value, step)
  if (next > today || next < minDay) return
  day.value = next
}

function applyMine(data, dayValue) {
  for (const key of MEALS) {
    const form = forms.value[key]
    form.rating = 0
    form.taste = ''
    form.pairing = ''
    form.portion = ''
    form.comment = ''
    form.existing = null
    const row = data?.[key]
    if (row && row.date === dayValue) {
      form.rating = row.rating
      form.taste = row.taste || ''
      form.pairing = row.pairing || ''
      form.portion = row.portion || ''
      form.comment = row.comment || ''
      form.existing = row
    }
  }
}

async function loadMine() {
  const data = await api.get('/reviews/mine', { day: day.value })
  applyMine(data, day.value)
}

async function loadMenus() {
  menus.value = (await api.get(`/menus/day/${day.value}`))?.meals || {}
}

async function loadHistory() {
  history.value = (await api.get('/reviews/history', { limit: 30 })) || []
}

async function openHistory() {
  showHistory.value = true
  if (!history.value.length) {
    loadHistory().catch((error) => showToast(error.message || '加载历史失败'))
  }
}

async function submit() {
  const form = current.value
  if (!form.rating) {
    showToast('先选一个评分吧')
    return
  }
  if (needReason.value && !form.taste && !form.pairing && !form.portion && !form.comment.trim()) {
    showToast('评分较低时请选一个原因')
    return
  }
  submitting.value = true
  try {
    await api.post('/reviews', {
      date: day.value,
      meal: meal.value,
      rating: form.rating,
      taste: form.taste,
      pairing: form.pairing,
      portion: form.portion,
      comment: form.comment.trim(),
    })
    showToast(`${MEAL_LABELS[meal.value]}评价已提交`)
    await Promise.all([loadMine(), loadHistory()])
  } catch (error) {
    showToast(error.message || '提交失败')
  } finally {
    submitting.value = false
  }
}

watch(day, () => {
  loading.value = true
  Promise.all([loadMine(), loadMenus()])
    .catch(() => {})
    .finally(() => {
      loading.value = false
    })
})

onMounted(async () => {
  /* 从菜单页带参跳转：/review?date=2026-11-10&meal=dinner */
  const queryDate = typeof route.query.date === 'string' ? route.query.date : ''
  if (/^\d{4}-\d{2}-\d{2}$/.test(queryDate) && queryDate <= today && queryDate >= minDay) {
    day.value = queryDate
  }
  if (MEALS.includes(route.query.meal)) {
    meal.value = route.query.meal
  }
  try {
    await Promise.all([loadMine(), loadMenus(), loadHistory()])
  } catch (error) {
    showToast(error.message || '加载失败')
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="review-page">
    <header class="head">
      <div>
        <h1>菜品评价</h1>
        <p class="sub">早中晚分开评，厨师看得见</p>
      </div>
      <button type="button" class="history-btn" @click="openHistory">
        <AppIcon name="clock" :size="15" />
        历史
      </button>
    </header>

    <div class="page">
      <div class="card date-card">
        <button type="button" class="nav" :disabled="day <= minDay" @click="shiftDay(-1)">
          <AppIcon name="chevron-left" :size="16" />
        </button>
        <div class="date-body">
          <strong>{{ fullDateLabel(day) }}</strong>
          <span class="muted small">
            {{ day === today ? '今天' : weekdayLabel(day) }}
            <template v-if="ratedCount"> · 已评 {{ ratedCount }}/3 餐</template>
          </span>
        </div>
        <button type="button" class="nav" :disabled="day >= today" @click="shiftDay(1)">
          <AppIcon name="chevron-right" :size="16" />
        </button>
      </div>

      <!-- 早/中/晚分段切换（参考小程序分段控件） -->
      <div class="seg" role="tablist">
        <button
          v-for="key in meals"
          :key="key"
          type="button"
          class="seg-item"
          :class="{ on: meal === key }"
          role="tab"
          :aria-selected="meal === key"
          @click="meal = key"
        >
          <span class="seg-ico"><AppIcon :name="key === 'breakfast' ? 'sparkles' : key === 'lunch' ? 'bowl' : 'utensils'" :size="15" /></span>
          {{ MEAL_LABELS[key] }}
          <i v-if="forms[key].existing" class="seg-dot" />
        </button>
      </div>

      <div class="card main-card">
        <div class="meal-row-head">
          <span class="meal-badge"><AppIcon :name="meal === 'breakfast' ? 'sparkles' : meal === 'lunch' ? 'bowl' : 'utensils'" :size="16" /></span>
          <div class="meal-head-text">
            <strong>{{ fullDateLabel(day) }} · {{ MEAL_LABELS[meal] }}</strong>
            <span v-if="menus[meal]?.dishes?.length" class="muted small menu-line">
              {{ menus[meal].dishes.map((dish) => dish.name).join('、') }}
            </span>
            <span v-else class="muted small">当餐菜单待上传</span>
          </div>
          <span v-if="current.existing" class="pill done">已评</span>
        </div>

        <p class="question">这顿饭你觉得怎么样？</p>

        <div class="ratings">
          <button
            v-for="item in ratingList"
            :key="item.value"
            type="button"
            class="rating"
            :class="{ active: current.rating === item.value, low: item.value <= 2 }"
            @click="pickRating(item.value)"
          >
            <span class="emoji">{{ item.emoji }}</span>
            <span class="text">{{ item.label }}</span>
          </button>
        </div>

        <div v-if="needReason" class="reasons pop-in">
          <p class="reason-title">
            <AppIcon name="info" :size="13" />
            哪里可以更好？至少选一项
          </p>

          <div class="reason-group">
            <span class="group-label">口味</span>
            <div class="chips">
              <button
                v-for="option in tasteOptions"
                :key="option"
                type="button"
                class="chip-btn"
                :class="{ on: current.taste === option }"
                @click="current.taste = current.taste === option ? '' : option"
              >
                {{ option }}
              </button>
            </div>
          </div>

          <div class="reason-group">
            <span class="group-label">搭配</span>
            <div class="chips">
              <button
                v-for="option in pairingOptions"
                :key="option"
                type="button"
                class="chip-btn"
                :class="{ on: current.pairing === option }"
                @click="current.pairing = current.pairing === option ? '' : option"
              >
                {{ option }}
              </button>
            </div>
          </div>

          <div class="reason-group">
            <span class="group-label">分量</span>
            <div class="chips">
              <button
                v-for="option in portionOptions"
                :key="option"
                type="button"
                class="chip-btn"
                :class="{ on: current.portion === option }"
                @click="current.portion = current.portion === option ? '' : option"
              >
                {{ option }}
              </button>
            </div>
          </div>
        </div>

        <van-field
          v-model="current.comment"
          type="textarea"
          rows="3"
          maxlength="200"
          show-word-limit
          :placeholder="needReason ? '补充说明（选填）' : '想吃点什么？想说的都可以写在这（选填）'"
          class="comment"
        />

        <button type="button" class="primary-btn full" :disabled="submitting" @click="submit">
          {{ submitting ? '提交中…' : current.existing ? `更新${MEAL_LABELS[meal]}评价` : `提交${MEAL_LABELS[meal]}评价` }}
        </button>
        <p v-if="current.existing" class="existing">
          已于 {{ formatDateTime(current.existing.created_at) }} 评价过「{{ ratingLabel(current.existing.rating) }}」，再次提交会覆盖。
        </p>
      </div>

      <section class="section">
        <div class="section-head">
          <h3>我的评价</h3>
          <button type="button" class="link" @click="openHistory">
            全部记录
            <AppIcon name="chevron-right" :size="14" />
          </button>
        </div>
        <div v-if="recentHistory.length" class="card history-card">
          <div v-for="item in recentHistory" :key="item.id" class="h-item">
            <div class="h-top">
              <span class="h-date">{{ item.date.slice(5) }}</span>
              <span class="h-meal">{{ item.meal_label || MEAL_LABELS[item.meal] || '' }}</span>
              <span class="h-rating" :class="{ low: item.rating <= 2 }">{{ item.rating_label }}</span>
              <span class="spacer" />
              <span class="muted small">{{ formatDateTime(item.created_at) }}</span>
            </div>
            <p v-if="reasonsText(item)" class="h-reasons">{{ reasonsText(item) }}</p>
            <p v-if="item.comment" class="h-comment">{{ item.comment }}</p>
          </div>
        </div>
        <div v-else class="empty">
          <AppIcon name="star" :size="26" />
          <span>还没有评价记录</span>
        </div>
      </section>
    </div>

    <van-popup teleport="body" v-model:show="showHistory" round position="bottom" :style="{ height: '76vh' }">
      <div class="sheet history-sheet">
        <div class="sheet-head">
          <h3>我的评价记录</h3>
          <span class="pill grey">{{ history.length }} 条</span>
          <span class="spacer" />
          <button type="button" class="close" @click="showHistory = false">
            <AppIcon name="close" :size="18" />
          </button>
        </div>
        <div class="sheet-body">
          <div v-if="!history.length" class="empty">
            <AppIcon name="star" :size="26" />
            <span>还没有评价记录</span>
          </div>
          <div v-for="item in history" :key="item.id" class="h-item">
            <div class="h-top">
              <span class="h-date">{{ item.date.slice(5) }}</span>
              <span class="h-meal">{{ item.meal_label || MEAL_LABELS[item.meal] || '' }}</span>
              <span class="h-rating" :class="{ low: item.rating <= 2 }">{{ item.rating_label }}</span>
              <span class="spacer" />
              <span class="muted small">{{ formatDateTime(item.created_at) }}</span>
            </div>
            <p v-if="reasonsText(item)" class="h-reasons">{{ reasonsText(item) }}</p>
            <p v-if="item.comment" class="h-comment">{{ item.comment }}</p>
          </div>
        </div>
      </div>
    </van-popup>
  </div>
</template>

<style scoped>
/* tabbar 之上留出呼吸空间，内容不再贴着底栏 */
.review-page {
  padding-bottom: calc(90px + env(safe-area-inset-bottom));
}

.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 16px 8px;
}

.head h1 {
  font-size: 22px;
  font-weight: 800;
  letter-spacing: 0.4px;
  color: var(--text);
}

.sub {
  margin-top: 3px;
  font-size: 12px;
  color: var(--text-3);
}

.history-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 34px;
  padding: 0 12px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--card);
  color: var(--text-2);
  font-size: 12px;
  font-weight: 600;
  font-family: inherit;
}

.history-btn:active {
  border-color: var(--brand);
  color: var(--brand-deep);
}

.small {
  font-size: 12px;
}

.date-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
}

.nav {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--card-2);
  color: var(--text-2);
}

.nav:disabled {
  opacity: 0.35;
}

.date-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.date-body strong {
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
}

/* 分段控件：早/中/晚 */
.seg {
  display: flex;
  gap: 4px;
  margin-top: 12px;
  padding: 4px;
  border-radius: 999px;
  background: var(--veil);
  border: 1px solid var(--line);
}

.seg-item {
  position: relative;
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 38px;
  border: none;
  border-radius: 999px;
  background: transparent;
  color: var(--text-2);
  font-size: 13px;
  font-weight: 600;
  font-family: inherit;
  transition: all 0.18s ease;
}

.seg-item.on {
  background: var(--grad-brand);
  color: #fff;
  box-shadow: 0 6px 14px rgba(5, 175, 240, 0.26);
}

.seg-ico {
  display: grid;
  place-items: center;
}

.seg-dot {
  position: absolute;
  top: 7px;
  right: 10px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--ok);
}

.seg-item.on .seg-dot {
  background: rgba(255, 255, 255, 0.9);
}

.main-card {
  margin-top: 12px;
  padding: 16px;
}

.meal-row-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--line);
}

.meal-badge {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  flex: none;
  border-radius: 12px;
  background: var(--brand-soft);
  color: var(--brand);
}

.meal-head-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.meal-head-text strong {
  font-size: 13px;
  font-weight: 700;
  color: var(--text);
}

.menu-line {
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.pill.done {
  padding: 3px 9px;
  border-radius: 999px;
  background: var(--ok-soft);
  color: var(--ok);
  font-size: 11px;
  font-weight: 600;
  flex: none;
}

.question {
  margin-top: 14px;
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
}

.ratings {
  display: flex;
  gap: 6px;
  margin-top: 12px;
}

.rating {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 10px 2px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--card-2);
  font-family: inherit;
  transition: all 0.18s ease;
}

.rating .emoji {
  font-size: 22px;
  filter: grayscale(0.5);
  transition: filter 0.18s ease, transform 0.18s ease;
}

.rating .text {
  font-size: 11px;
  color: var(--text-2);
  font-weight: 600;
}

.rating.active {
  border-color: transparent;
  background: var(--brand-soft);
  box-shadow: inset 0 0 0 1.5px var(--brand);
  transform: translateY(-2px);
}

.rating.active .emoji {
  filter: none;
  transform: scale(1.08);
}

.rating.active .text {
  color: var(--brand-dark);
}

.rating.low.active {
  background: var(--danger-soft);
  box-shadow: inset 0 0 0 1.5px var(--danger);
}

.rating.low.active .text {
  color: var(--danger);
}

.reasons {
  margin-top: 14px;
  padding: 12px;
  border-radius: 14px;
  background: var(--card-2);
  border: 1px dashed var(--line);
}

.reason-title {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-bottom: 10px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-2);
}

.reason-group {
  margin-bottom: 10px;
}

.reason-group:last-child {
  margin-bottom: 0;
}

.group-label {
  font-size: 11px;
  color: var(--text-3);
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
}

.chip-btn {
  padding: 6px 11px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--card);
  color: var(--text-2);
  font-size: 12px;
  font-family: inherit;
  transition: all 0.16s ease;
}

.chip-btn.on {
  border-color: transparent;
  background: var(--grad-brand);
  color: #fff;
  box-shadow: 0 6px 14px rgba(5, 175, 240, 0.26);
}

.comment {
  margin-top: 14px;
  border-radius: 14px;
  background: var(--card-2);
  border: 1px solid var(--line);
  overflow: hidden;
}

.full {
  width: 100%;
  margin-top: 16px;
}

.existing {
  margin-top: 10px;
  text-align: center;
  font-size: 11px;
  color: var(--text-3);
}

.history-card {
  padding: 4px 14px;
}

.h-item {
  padding: 12px 0;
  border-bottom: 1px solid var(--line);
}

.h-item:last-child {
  border-bottom: none;
}

.h-top {
  display: flex;
  align-items: center;
  gap: 8px;
}

.h-date {
  font-size: 12px;
  color: var(--text-2);
  font-weight: 600;
}

.h-meal {
  padding: 2px 7px;
  border-radius: 7px;
  background: var(--brand-soft);
  color: var(--brand-dark);
  font-size: 11px;
  font-weight: 600;
}

.h-rating {
  padding: 2px 8px;
  border-radius: 7px;
  background: var(--ok-soft);
  color: var(--ok);
  font-size: 11px;
  font-weight: 600;
}

.h-rating.low {
  background: var(--danger-soft);
  color: var(--danger);
}

.h-reasons {
  margin-top: 6px;
  font-size: 11px;
  color: var(--brand-dark);
}

.h-comment {
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-2);
  line-height: 1.6;
}

/* 弹层骨架复用 base.css 的 .sheet/.sheet-head/.sheet-body，这里只补充数量徽标 */
</style>
