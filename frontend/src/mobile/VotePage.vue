<script setup>
import { computed, onMounted, ref } from 'vue'
import { showToast } from 'vant'
import { useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import { api } from '../api/client'
import { monthDay, todayISO, weekStartOf, weekdayLabel } from '../utils/date'

const router = useRouter()

const today = todayISO()
const weekStart = ref(weekStartOf(today))
const voteOpen = ref(true)
const voteReason = ref('')
const voteDays = ref([])
const myVotes = ref([])
const draftVotes = ref([])
const voters = ref(0)
const totalPicks = ref(0)
const activeDay = ref(today)
const voteAnim = ref('')
const saving = ref(false)
const showRank = ref(false)
const ranking = ref([])
const rankLoading = ref(false)

/* 只显示有菜单的天（周末无菜单自动不出现） */
const voteDaysInRange = computed(() => voteDays.value.filter((day) => day.meals?.some((meal) => meal.dishes?.length)))

const activeDayData = computed(
  () => voteDaysInRange.value.find((day) => day.date === activeDay.value) || voteDaysInRange.value[0] || null,
)

/* 当天去重后的菜品列表，label 标注来自哪一餐 */
const activeDishes = computed(() => {
  const day = activeDayData.value
  if (!day) return []
  const seen = new Set()
  const list = []
  day.meals.forEach((meal) => {
    ;(meal.dishes || []).forEach((name) => {
      if (seen.has(name)) return
      seen.add(name)
      list.push({ name, meal: meal.meal, label: meal.label })
    })
  })
  return list
})

const dirtyVotes = computed(() => {
  const before = [...myVotes.value].sort().join('|')
  const after = [...draftVotes.value].sort().join('|')
  return before !== after
})

/* 每天已选数量角标 */
const dayPickCount = computed(() => {
  const map = {}
  voteDays.value.forEach((day) => {
    const names = new Set()
    day.meals.forEach((meal) => (meal.dishes || []).forEach((name) => names.add(name)))
    map[day.date] = draftVotes.value.filter((name) => names.has(name)).length
  })
  return map
})

async function loadVotes() {
  try {
    const data = await api.get('/votes/options', { week_start: weekStart.value })
    voteOpen.value = data.open
    voteReason.value = data.reason || ''
    voteDays.value = data.days || []
    myVotes.value = data.my_votes || []
    draftVotes.value = data.my_votes || []
    if (!voteDaysInRange.value.some((day) => day.date === activeDay.value)) {
      activeDay.value = voteDaysInRange.value[0]?.date || today
    }
  } catch (error) {
    showToast(error.message || '投票加载失败')
  }
}

function toggleVote(name) {
  if (!voteOpen.value) {
    showToast(voteReason.value || '本周投票已关闭')
    return
  }
  const set = new Set(draftVotes.value)
  if (set.has(name)) set.delete(name)
  else set.add(name)
  draftVotes.value = [...set]
}

function pickDay(date) {
  if (date === activeDay.value) return
  const from = voteDaysInRange.value.findIndex((day) => day.date === activeDay.value)
  const to = voteDaysInRange.value.findIndex((day) => day.date === date)
  voteAnim.value = to >= from ? 'slide-right' : 'slide-left'
  activeDay.value = date
  window.setTimeout(() => {
    voteAnim.value = ''
  }, 320)
}

/* 跟手滑动切天 */
const voteTouch = { x: 0, y: 0, active: false, start: 0 }
const voteDragX = ref(0)
const voteDragging = ref(false)
const voteDragStyle = computed(() =>
  voteDragging.value ? { transform: `translateX(${voteDragX.value}px)`, transition: 'none' } : {},
)

function onVoteTouchStart(event) {
  const point = event.touches ? event.touches[0] : event
  voteTouch.x = point.clientX
  voteTouch.y = point.clientY
  voteTouch.active = true
  voteTouch.start = Date.now()
  voteDragging.value = true
  voteDragX.value = 0
}

function onVoteTouchMove(event) {
  if (!voteTouch.active) return
  const point = event.touches ? event.touches[0] : event
  const dx = point.clientX - voteTouch.x
  const dy = point.clientY - voteTouch.y
  if (Math.abs(dx) < Math.abs(dy) && Math.abs(dy) > 8) {
    voteDragX.value = 0
    return
  }
  voteDragX.value = Math.sign(dx) * Math.min(Math.abs(dx) * 0.72, 84)
}

function onVoteTouchEnd(event) {
  if (!voteTouch.active) return
  voteTouch.active = false
  const point = event.changedTouches ? event.changedTouches[0] : event
  const dx = point.clientX - voteTouch.x
  const dy = point.clientY - voteTouch.y
  const elapsed = Math.max(Date.now() - voteTouch.start, 1)
  voteDragging.value = false
  voteDragX.value = 0
  if (Math.abs(dx) < Math.abs(dy) * 1.2) return
  const flick = Math.abs(dx) > 22 && Math.abs(dx) / elapsed > 0.35
  if (Math.abs(dx) < 46 && !flick) return
  const list = voteDaysInRange.value
  const index = list.findIndex((day) => day.date === activeDay.value)
  const next = list[index + (dx < 0 ? 1 : -1)]
  if (next) pickDay(next.date)
}

async function submitVotes() {
  if (!dirtyVotes.value || saving.value) return
  saving.value = true
  try {
    const result = await api.post('/votes', {
      week_start: weekStart.value,
      dish_names: draftVotes.value,
    })
    myVotes.value = result.my_votes || []
    draftVotes.value = result.my_votes || []
    showToast(result.message || '投票已保存')
    await loadVotes()
  } catch (error) {
    showToast(error.message || '投票失败')
  } finally {
    saving.value = false
  }
}

async function loadRanking(show = true) {
  if (show) showRank.value = true
  rankLoading.value = true
  try {
    const data = await api.get('/votes/results', { week_start: weekStart.value })
    ranking.value = data.ranking || []
    voters.value = data.total_votes ?? 0
    totalPicks.value = data.total_picks ?? 0
  } catch (error) {
    if (show) showToast(error.message || '排行榜加载失败')
  } finally {
    rankLoading.value = false
  }
}

function openRanking() {
  loadRanking(true)
}

onMounted(() => {
  loadVotes()
  /* 只静默预载票数，不主动弹排行榜 */
  loadRanking(false)
})
</script>

<template>
  <div class="vote-page">
    <header class="head">
      <button type="button" class="back" @click="router.back()">
        <AppIcon name="chevron-left" :size="18" />
      </button>
      <div>
        <h1>本周最爱菜投票</h1>
        <p class="sub">选这周你最想吃的菜，可多选</p>
      </div>
      <button type="button" class="rank-btn" @click="openRanking">
        <AppIcon name="chart" :size="15" />
        排行榜
      </button>
    </header>

    <div class="page">
      <div v-if="!voteOpen" class="card closed-card">
        <AppIcon name="lock" :size="16" />
        {{ voteReason || '本周投票未开放' }}
      </div>

      <template v-else>
        <div class="hscroll day-chips">
          <button
            v-for="day in voteDaysInRange"
            :key="day.date"
            type="button"
            class="chip"
            :class="{ active: day.date === activeDayData?.date }"
            @click="pickDay(day.date)"
          >
            {{ day.date === today ? '今天' : weekdayLabel(day.date) }}
            <i>{{ monthDay(day.date) }}</i>
            <em v-if="dayPickCount[day.date]" class="day-badge">{{ dayPickCount[day.date] }}</em>
          </button>
        </div>

        <div class="card pick-card">
          <div
            class="vote-swipe"
            :style="voteDragStyle"
            @touchstart.passive="onVoteTouchStart"
            @touchmove.passive="onVoteTouchMove"
            @touchend.passive="onVoteTouchEnd"
            @touchcancel.passive="onVoteTouchEnd"
            @mousedown="onVoteTouchStart"
            @mousemove="onVoteTouchMove"
            @mouseup="onVoteTouchEnd"
            @mouseleave="onVoteTouchEnd"
          >
            <div :key="activeDayData?.date" :class="voteAnim">
              <div v-if="activeDishes.length" class="dish-grid">
                <button
                  v-for="dish in activeDishes"
                  :key="dish.name"
                  type="button"
                  class="vote-dish"
                  :class="{ on: draftVotes.includes(dish.name) }"
                  @click="toggleVote(dish.name)"
                >
                  <span class="vote-dish-name">{{ dish.name }}</span>
                  <span class="vote-dish-meal">{{ dish.label }}</span>
                  <i v-if="draftVotes.includes(dish.name)" class="vote-check">
                    <AppIcon name="check" :size="11" :stroke-width="3" />
                  </i>
                </button>
              </div>
              <div v-else class="empty">
                <AppIcon name="bowl" :size="26" />
                <span>这一天还没有菜单</span>
              </div>
            </div>
          </div>

          <p class="muted small hint">左右滑动切换日期 · 最多可选 10 道</p>
        </div>

        <button
          type="button"
          class="primary-btn full"
          :disabled="!dirtyVotes || saving"
          @click="submitVotes"
        >
          {{ saving ? '提交中…' : dirtyVotes ? `提交投票（已选 ${draftVotes.length}）` : '投票已保存，可继续改' }}
        </button>
      </template>
    </div>

    <van-popup teleport="body" v-model:show="showRank" round position="bottom" :style="{ height: '72vh' }">
      <div class="sheet">
        <div class="sheet-head">
          <h3>本周最爱菜排行</h3>
          <span class="pill grey">{{ voters }} 人 · {{ totalPicks }} 票</span>
          <span class="spacer" />
          <button type="button" class="close" @click="showRank = false">
            <AppIcon name="close" :size="18" />
          </button>
        </div>
        <div class="sheet-body">
          <div v-if="rankLoading" class="empty">加载中…</div>
          <div v-else-if="ranking.length" class="rank-list">
            <div v-for="item in ranking" :key="item.dish_name" class="rank-item">
              <span class="rank-no" :class="{ top: item.rank <= 3 }">{{ item.rank }}</span>
              <span class="rank-name">{{ item.dish_name }}</span>
              <span class="rank-bar">
                <i :style="{ width: `${Math.min(item.percent, 100)}%` }" />
              </span>
              <span class="rank-votes">{{ item.votes }} 票</span>
            </div>
          </div>
          <div v-else class="empty">
            <AppIcon name="chart" :size="26" />
            <span>还没有人投票</span>
          </div>
        </div>
      </div>
    </van-popup>
  </div>
</template>

<style scoped>
.vote-page {
  padding-bottom: calc(40px + env(safe-area-inset-bottom));
}

.head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 18px 16px 10px;
}

.back {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  flex: none;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--card);
  color: var(--text-2);
}

.head h1 {
  font-size: 20px;
  font-weight: 800;
  letter-spacing: 0.3px;
  color: var(--text);
}

.head > div {
  flex: 1;
  min-width: 0;
}

.sub {
  margin-top: 2px;
  font-size: 12px;
  color: var(--text-3);
}

.rank-btn {
  flex: none;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 34px;
  padding: 0 12px;
  border: none;
  border-radius: 999px;
  background: var(--brand-soft);
  color: var(--brand-dark);
  font-size: 12px;
  font-weight: 600;
  font-family: inherit;
}

.rank-btn:active {
  transform: scale(0.96);
}

.page {
  padding: 0 16px;
}

.closed-card {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 28px 16px;
  color: var(--text-2);
  font-size: 13px;
}

.day-chips {
  display: flex;
  gap: 8px;
  padding-bottom: 4px;
}

.chip {
  position: relative;
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
  min-width: 58px;
  padding: 7px 10px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--card);
  color: var(--text-2);
  font-size: 12px;
  font-weight: 600;
  font-family: inherit;
  flex: none;
}

.chip i {
  font-style: normal;
  font-size: 10px;
  color: var(--text-3);
  font-weight: 500;
}

.chip.active {
  border-color: transparent;
  background: var(--grad-brand);
  color: #fff;
  box-shadow: 0 6px 14px rgba(5, 175, 240, 0.26);
}

.chip.active i {
  color: rgba(255, 255, 255, 0.82);
}

.day-badge {
  position: absolute;
  top: 4px;
  right: 4px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: var(--ok);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  font-style: normal;
}

.chip.active .day-badge {
  background: #fff;
  color: var(--brand-dark);
}

.pick-card {
  margin-top: 12px;
  padding: 14px;
}

.vote-swipe {
  touch-action: pan-y;
  will-change: transform;
}

.vote-swipe > div {
  transition: transform 0.24s cubic-bezier(0.22, 0.68, 0.35, 1);
}

.vote-swipe > div.slide-right {
  animation: slide-right 0.28s ease both;
}

.vote-swipe > div.slide-left {
  animation: slide-left 0.28s ease both;
}

@keyframes slide-right {
  from {
    opacity: 0;
    transform: translateX(26px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes slide-left {
  from {
    opacity: 0;
    transform: translateX(-26px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.dish-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.vote-dish {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  padding: 11px 12px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--card-2);
  text-align: left;
  font-family: inherit;
  transition: all 0.16s ease;
}

.vote-dish:active {
  transform: scale(0.97);
}

.vote-dish.on {
  border-color: transparent;
  background: var(--brand-soft);
  box-shadow: inset 0 0 0 1.5px var(--brand);
}

.vote-dish-name {
  font-size: 13px;
  font-weight: 700;
  color: var(--text);
}

.vote-dish-meal {
  font-size: 10px;
  color: var(--text-3);
}

.vote-check {
  position: absolute;
  top: 8px;
  right: 8px;
  display: grid;
  place-items: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--brand);
  color: #fff;
}

.hint {
  margin-top: 12px;
  text-align: center;
}

.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 30px 0;
  color: var(--text-3);
  font-size: 12px;
}

.full {
  width: 100%;
  margin-top: 14px;
}

.pill.grey {
  padding: 3px 9px;
  border-radius: 999px;
  background: var(--card-2);
  color: var(--text-3);
  font-size: 11px;
  font-weight: 600;
}

.rank-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.rank-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 0;
}

.rank-no {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  flex: none;
  border-radius: 8px;
  background: var(--card-2);
  color: var(--text-3);
  font-size: 12px;
  font-weight: 700;
}

.rank-no.top {
  background: var(--grad-brand);
  color: #fff;
}

.rank-name {
  width: 110px;
  flex: none;
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rank-bar {
  flex: 1;
  height: 8px;
  border-radius: 999px;
  background: var(--veil);
  overflow: hidden;
}

.rank-bar i {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: var(--grad-brand);
}

.rank-votes {
  flex: none;
  width: 46px;
  text-align: right;
  font-size: 12px;
  color: var(--text-2);
}
</style>
