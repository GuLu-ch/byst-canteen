<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { showConfirmDialog, showToast } from 'vant'
import AppIcon from '../components/AppIcon.vue'
import { api } from '../api/client'
import { store } from '../stores/app'
import { MEAL_LABELS, addDays, monthDay, todayISO, weekStartOf, weekdayLabel } from '../utils/date'

const MEALS = ['breakfast', 'lunch', 'dinner']
const MEAL_ICONS = { breakfast: 'sparkles', lunch: 'bowl', dinner: 'utensils' }

const TYPE_CLASS = {
  荤菜: 'meat',
  素菜: 'veg',
  汤品: 'soup',
  主食: 'staple',
  凉菜: 'cold',
  小菜: 'side',
}

const today = todayISO()
const router = useRouter()
const openDays = computed(() => store.settings?.open_days || 7)
const mealTimes = computed(() => store.settings?.meal_times || {})

const weekStart = ref(weekStartOf(today))
const selected = ref(today)
const weekDays = ref([])
const avail = ref({})
const mineMap = ref({})
const draft = ref({})
const original = ref({})
const loading = ref(false)
const saving = ref(false)
const animClass = ref('')

const weekDates = computed(() => Array.from({ length: 7 }, (_, i) => addDays(weekStart.value, i)))
const isCurrentWeek = computed(() => weekStart.value === weekStartOf(today))

function keyOf(date, meal) {
  return `${date}|${meal}`
}

function stateOf(date, meal) {
  return avail.value[date]?.[meal] || { open: false, reason: '该日期暂不可预约', deadline: '' }
}

function menuOf(date) {
  return weekDays.value.find((item) => item.date === date) || null
}

const dayMenu = computed(() => menuOf(selected.value))

const meals = computed(() =>
  MEALS.map((meal) => ({
    meal,
    label: MEAL_LABELS[meal],
    time: mealTimes.value[meal] || '',
    menu: dayMenu.value?.meals?.[meal] || null,
    state: stateOf(selected.value, meal),
    picked: !!draft.value[keyOf(selected.value, meal)],
  })),
)

const pickedCount = computed(() => MEALS.filter((meal) => draft.value[keyOf(selected.value, meal)]).length)

const pendingChanges = computed(() => {
  const keys = new Set([...Object.keys(draft.value), ...Object.keys(original.value)])
  const adds = []
  const dels = []
  keys.forEach((key) => {
    const want = !!draft.value[key]
    const before = !!original.value[key]
    if (want === before) return
    const [date, meal] = key.split('|')
    if (want) adds.push({ date, meal })
    else if (mineMap.value[key]) dels.push(mineMap.value[key].id)
  })
  return { adds, dels, count: adds.length + dels.length }
})

/* 未保存改动数（全周口径，action-bar 与徽标共用） */
const weekPending = computed(() => pendingChanges.value.count)

function reservedCount(date) {
  return MEALS.filter((meal) => draft.value[keyOf(date, meal)]).length
}

async function load(keepSelection = true) {
  loading.value = true
  try {
    const first = weekDates.value[0] < today ? weekDates.value[0] : today
    const later = addDays(today, openDays.value - 1)
    const last = later > weekDates.value[6] ? later : weekDates.value[6]
    const [week, av, mine] = await Promise.all([
      api.get('/menus/week', { week_start: weekStart.value }),
      api.get('/reservations/availability', { start: first, end: last }),
      api.get('/reservations/mine', { start: first, end: last }),
    ])
    weekDays.value = week.days || []
    avail.value = Object.fromEntries((av.days || []).map((day) => [day.date, day.meals]))
    const map = {}
    ;(mine.items || []).forEach((item) => {
      map[keyOf(item.date, item.meal)] = item
    })
    mineMap.value = map

    const draftNext = {}
    const originalNext = {}
    weekDates.value.forEach((date) => {
      MEALS.forEach((meal) => {
        const key = keyOf(date, meal)
        const reserved = !!map[key]
        draftNext[key] = reserved
        originalNext[key] = reserved
      })
    })
    draft.value = draftNext
    original.value = originalNext
    if (!keepSelection || !weekDates.value.includes(selected.value)) {
      selected.value = weekDates.value.includes(today) ? today : weekDates.value[0]
    }
  } catch (error) {
    showToast(error.message || '菜单加载失败')
  } finally {
    loading.value = false
  }
}

async function guardDirty() {
  if (!weekPending.value) return true
  try {
    await showConfirmDialog({
      title: '还有未保存的预约',
      message: '切换后将丢弃当前的修改，确定要离开吗？',
      confirmButtonText: '放弃修改',
      cancelButtonText: '继续编辑',
    })
    return true
  } catch {
    return false
  }
}

async function selectDay(date) {
  if (date === selected.value) return
  const from = weekDates.value.indexOf(selected.value)
  const to = weekDates.value.indexOf(date)
  animClass.value = to > from ? 'slide-right' : 'slide-left'
  selected.value = date
}

async function changeWeek(delta) {
  if (!(await guardDirty())) return
  weekStart.value = addDays(weekStart.value, delta * 7)
  selected.value = weekStart.value
  await load(false)
}

const touch = { x: 0, y: 0, active: false, start: 0 }

// 手指跟手位移（silky 的关键：拖动时内容跟着走，松手再吸附/翻页）
const dragX = ref(0)
const dragging = ref(false)
const dragStyle = computed(() =>
  dragging.value ? { transform: `translateX(${dragX.value}px)`, transition: 'none' } : {},
)

function beginDrag(event) {
  const point = event.touches ? event.touches[0] : event
  touch.x = point.clientX
  touch.y = point.clientY
  touch.active = true
  touch.start = Date.now()
  dragX.value = 0
  dragging.value = true
}

function moveDrag(event) {
  if (!touch.active) return
  const point = event.touches ? event.touches[0] : event
  const dx = point.clientX - touch.x
  const dy = point.clientY - touch.y
  // 横向意图不明显时不抢滚动：只做轻微跟手，纵向位移交给页面滚动
  if (Math.abs(dx) < Math.abs(dy) && Math.abs(dy) > 8) {
    dragX.value = 0
    return
  }
  const limit = 96
  const resisted = Math.sign(dx) * Math.min(Math.abs(dx) * 0.72, limit)
  dragX.value = resisted
}

function endDrag(event) {
  if (!touch.active) return
  touch.active = false
  const point = event.changedTouches ? event.changedTouches[0] : event
  const dx = point.clientX - touch.x
  const dy = point.clientY - touch.y
  const elapsed = Math.max(Date.now() - touch.start, 1)
  const velocity = Math.abs(dx) / elapsed // px/ms
  dragging.value = false
  dragX.value = 0
  const horizontal = Math.abs(dx) > Math.abs(dy) * 1.2
  const flick = Math.abs(dx) > 22 && velocity > 0.35
  if (!horizontal) return
  if (Math.abs(dx) < 46 && !flick) return
  stepDay(dx < 0 ? 1 : -1)
}

function cancelDrag() {
  touch.active = false
  dragging.value = false
  dragX.value = 0
}

async function stepDay(delta) {
  const index = weekDates.value.indexOf(selected.value)
  const nextIndex = index + delta
  if (nextIndex >= 0 && nextIndex <= 6) {
    animClass.value = delta > 0 ? 'slide-right' : 'slide-left'
    selected.value = weekDates.value[nextIndex]
    return
  }
  if (!(await guardDirty())) return
  weekStart.value = addDays(weekStart.value, delta > 0 ? 7 : -7)
  await load(false)
  selected.value = delta > 0 ? weekDates.value[0] : weekDates.value[6]
  animClass.value = delta > 0 ? 'slide-right' : 'slide-left'
}

function toggleMeal(meal) {
  const key = keyOf(selected.value, meal)
  const state = stateOf(selected.value, meal)
  if (!state.open) {
    showToast(state.reason || '该餐暂不可预约')
    return
  }
  draft.value = { ...draft.value, [key]: !draft.value[key] }
}

function pickAll(value) {
  const next = { ...draft.value }
  MEALS.forEach((meal) => {
    const key = keyOf(selected.value, meal)
    if (value && !stateOf(selected.value, meal).open) return
    next[key] = value
  })
  draft.value = next
}

function copyFrom(sourceDate, label) {
  if (!sourceDate) return
  const next = { ...draft.value }
  let copied = 0
  MEALS.forEach((meal) => {
    const target = keyOf(selected.value, meal)
    if (!stateOf(selected.value, meal).open) return
    next[target] = !!draft.value[keyOf(sourceDate, meal)]
    copied += 1
  })
  draft.value = next
  showToast(`${label}的安排已套用（${copied} 餐）`)
}

async function save() {
  const { adds, dels } = pendingChanges.value
  if (!adds.length && !dels.length) return
  saving.value = true
  const failed = []
  try {
    if (adds.length) {
      const result = await api.post('/reservations/bulk', { items: adds })
      ;(result.skipped || []).forEach((item) => failed.push(`${monthDay(item.date)} ${MEAL_LABELS[item.meal]}：${item.reason}`))
    }
    for (const id of dels) {
      try {
        await api.del(`/reservations/${id}`)
      } catch (error) {
        failed.push(error.message)
      }
    }
    await load()
    if (failed.length) showToast(failed[0])
    else showToast(`已更新 ${adds.length + dels.length} 处预约`)
  } catch (error) {
    showToast(error.message || '保存失败')
  } finally {
    saving.value = false
  }
}

watch(selected, () => {
  animClass.value = animClass.value || 'slide-right'
  window.setTimeout(() => {
    animClass.value = ''
  }, 320)
})

onMounted(() => load(false))
</script>

<template>
  <div class="page menu-page">
    <header class="week-bar">
      <div class="week-top">
        <button type="button" class="nav-btn" @click="changeWeek(-1)">
          <AppIcon name="chevron-left" :size="18" />
        </button>
        <div class="week-title">
          <strong>{{ monthDay(weekDates[0]) }} - {{ monthDay(weekDates[6]) }}</strong>
          <span class="pill" :class="{ grey: !isCurrentWeek }">{{ isCurrentWeek ? '本周' : '非本周' }}</span>
        </div>
        <button type="button" class="nav-btn" @click="changeWeek(1)">
          <AppIcon name="chevron-right" :size="18" />
        </button>
      </div>

      <!-- badge 放在 chip 内部右上角，不再被 sticky 头裁切 -->
      <div class="hscroll days">
        <button
          v-for="date in weekDates"
          :key="date"
          type="button"
          class="day"
          :class="{ active: date === selected, today: date === today, past: date < today }"
          @click="selectDay(date)"
        >
          <span v-if="reservedCount(date)" class="badge">{{ reservedCount(date) }}</span>
          <span class="wd">{{ date === today ? '今天' : weekdayLabel(date) }}</span>
          <span class="num">{{ monthDay(date) }}</span>
        </button>
      </div>
    </header>

    <div
      class="swipe-area"
      :style="dragStyle"
      @touchstart.passive="beginDrag"
      @touchmove.passive="moveDrag"
      @touchend.passive="endDrag"
      @touchcancel.passive="cancelDrag"
      @mousedown="beginDrag"
      @mousemove="moveDrag"
      @mouseup="endDrag"
      @mouseleave="cancelDrag"
    >
      <div :key="selected" :class="animClass">
        <div class="day-head">
          <span class="day-title">{{ monthDay(selected) }} {{ weekdayLabel(selected) }}</span>
          <span v-if="selected === today" class="pill">今天</span>
          <span v-else-if="selected === addDays(today, 1)" class="pill">明天</span>
          <span class="spacer" />
          <span class="muted small">
            <template v-if="pickedCount">本日已选 {{ pickedCount }} 餐</template>
            <template v-else>滑动可切换日期</template>
          </span>
        </div>

        <div class="quick hscroll">
          <button type="button" class="ghost-btn" @click="pickAll(true)">全选本日</button>
          <button type="button" class="ghost-btn" @click="pickAll(false)">清空本日</button>
          <button type="button" class="ghost-btn" @click="copyFrom(addDays(selected, -1), '同上一日')">
            <AppIcon name="refresh" :size="14" /> 同上一日
          </button>
          <button type="button" class="ghost-btn" @click="copyFrom(addDays(selected, -7), '同上一周')">
            <AppIcon name="refresh" :size="14" /> 同上一周
          </button>
        </div>

        <section
          v-for="item in meals"
          :key="item.meal"
          class="meal-card"
          :class="{ picked: item.picked, locked: !item.state.open }"
        >
          <div class="meal-top">
            <span class="meal-ico" :class="item.meal">
              <AppIcon :name="MEAL_ICONS[item.meal]" :size="18" />
            </span>
            <div class="meal-meta">
              <h4>{{ item.label }}</h4>
              <p class="muted small">{{ item.time }}</p>
            </div>
            <span class="spacer" />
            <button
              type="button"
              class="pick-btn"
              :class="{ on: item.picked }"
              @click="toggleMeal(item.meal)"
            >
              <AppIcon :name="item.picked ? 'check' : 'plus'" :size="15" :stroke-width="2.2" />
              {{ item.picked ? '已预约' : item.state.open ? '预约' : '不可约' }}
            </button>
          </div>

          <div v-if="item.menu && item.menu.dishes?.length" class="dishes">
            <span v-for="dish in item.menu.dishes" :key="dish.name" class="dish">
              {{ dish.name }}
              <i class="type" :class="TYPE_CLASS[dish.type] || 'side'">{{ dish.type }}</i>
            </span>
          </div>
          <p v-else class="empty-line">厨师还没有上传这一餐的菜单</p>

          <p v-if="item.menu?.note" class="meal-note"><AppIcon name="edit" :size="12" /> {{ item.menu.note }}</p>

          <p v-if="!item.state.open" class="meal-tip locked-tip">
            <AppIcon name="lock" :size="13" /> {{ item.state.reason }}
          </p>
          <p v-else class="meal-tip">
            <AppIcon name="clock" :size="13" /> 预约截止：{{ item.state.deadline?.replace('T', ' ') || '就餐前一天' }}
          </p>

          <button
            v-if="selected <= today"
            type="button"
            class="review-link"
            @click="router.push({ path: '/review', query: { date: selected, meal: item.meal } })"
          >
            <AppIcon name="star" :size="14" />
            <span>{{ selected === today ? `评价今天的${item.label}` : `评价${monthDay(selected)}的${item.label}` }}</span>
            <i class="chev"><AppIcon name="chevron-right" :size="14" /></i>
          </button>
        </section>
      </div>
    </div>

    <!-- 常驻底部保存条：z-index 35 高于 tabbar，随时可点，不用滚到底 -->
    <div class="action-bar">
      <div class="action-summary">
        <span class="strong">{{ pickedCount }} 餐</span>
        <span class="muted small">本日已选</span>
        <span v-if="weekPending" class="pill amber">{{ weekPending }} 处未保存</span>
      </div>
      <button
        type="button"
        class="primary-btn"
        :disabled="!weekPending || saving"
        @click="save"
      >
        {{ saving ? '保存中…' : weekPending ? `保存 ${weekPending} 处修改` : '暂无修改' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.menu-page {
  padding-top: 14px;
  /* 悬浮保存条(约64px+8px 间隙) + tabbar(58px) + 余量：滚到底时最后一张卡不被遮挡 */
  padding-bottom: calc(178px + env(safe-area-inset-bottom));
}

.week-bar {
  position: sticky;
  top: 0;
  z-index: 15;
  margin: -14px -16px 12px;
  padding: 14px 16px 12px;
  background: var(--veil);
  backdrop-filter: blur(12px);
}

.week-top {
  display: flex;
  align-items: center;
  gap: 8px;
}

.week-title {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 15px;
}

.week-title strong {
  font-weight: 700;
  color: var(--text);
}

.nav-btn {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--card);
  color: var(--text-2);
}

.nav-btn:active {
  background: var(--brand-soft);
  border-color: var(--brand);
  color: var(--brand-dark);
}

.days {
  margin-top: 12px;
  padding-bottom: 2px;
}

.day {
  position: relative;
  flex: none;
  width: 58px;
  padding: 8px 0 7px;
  border: 1px solid transparent;
  border-radius: 16px;
  background: var(--card);
  color: var(--text-2);
  box-shadow: var(--shadow-sm);
  transition: transform 0.18s ease, background 0.2s ease, color 0.2s ease, box-shadow 0.2s ease;
}

.day .wd {
  display: block;
  font-size: 11px;
  font-weight: 600;
}

.day .num {
  display: block;
  margin-top: 2px;
  font-size: 13px;
  font-weight: 700;
  color: var(--text);
}

.day.today .wd {
  color: var(--brand-deep);
}

.day.past {
  opacity: 0.55;
}

.day.active {
  background: var(--grad-brand);
  color: #fff;
  box-shadow: var(--shadow-brand);
  transform: translateY(-2px);
}

.day.active .num,
.day.active .wd {
  color: #fff;
}

/* badge 内嵌在 chip 右上角，绝不超出 chip 边界 */
.badge {
  position: absolute;
  top: 4px;
  right: 4px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: 999px;
  background: var(--brand-deep);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  line-height: 16px;
  text-align: center;
  box-shadow: 0 2px 6px rgba(5, 175, 240, 0.4);
}

.day.active .badge {
  background: rgba(255, 255, 255, 0.28);
  color: #fff;
}

.swipe-area {
  touch-action: pan-y;
  transition: transform 0.24s cubic-bezier(0.22, 0.68, 0.35, 1);
  will-change: transform;
}

.day-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 4px 2px 10px;
}

.day-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--text);
}

.small {
  font-size: 12px;
}

.quick {
  margin-bottom: 12px;
  padding-bottom: 2px;
}

.quick .ghost-btn {
  flex: none;
  height: 34px;
  padding: 0 12px;
  font-size: 12px;
}

.meal-card {
  margin-bottom: 12px;
  padding: 14px;
  border-radius: var(--radius);
  background: var(--card);
  border: 1px solid transparent;
  box-shadow: var(--shadow-sm);
  transition: border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}

.meal-card.picked {
  border-color: rgba(5, 175, 240, 0.5);
  background: var(--brand-softer);
  box-shadow: 0 8px 22px rgba(5, 175, 240, 0.12);
}

.meal-card.locked {
  opacity: 0.82;
}

.meal-top {
  display: flex;
  align-items: center;
  gap: 10px;
}

.meal-ico {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: 12px;
  background: var(--brand-soft);
  color: var(--brand-deep);
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

.meal-meta h4 {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
}

.pick-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 32px;
  padding: 0 12px;
  border: 1px solid var(--brand);
  border-radius: 999px;
  background: var(--card);
  color: var(--brand-deep);
  font-size: 13px;
  font-weight: 600;
  font-family: inherit;
  transition: all 0.18s ease;
}

.pick-btn.on {
  background: var(--grad-brand);
  border-color: transparent;
  color: #fff;
  box-shadow: 0 6px 14px rgba(3, 105, 161, 0.3);
}

.meal-card.locked .pick-btn {
  border-color: var(--line);
  color: var(--text-3);
}

.dishes {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 12px;
}

.dish {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 9px;
  border-radius: 10px;
  background: var(--card-2);
  font-size: 13px;
  color: var(--text);
}

.dish .type {
  font-style: normal;
  font-size: 10px;
  font-weight: 600;
  padding: 1px 5px;
  border-radius: 6px;
  background: var(--card);
  color: var(--text-3);
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

.empty-line {
  margin-top: 12px;
  color: var(--text-3);
  font-size: 13px;
}

.meal-note {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 10px;
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(247, 144, 9, 0.12);
  color: var(--amber);
  font-size: 12px;
}

.meal-tip {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 10px;
  font-size: 11px;
  color: var(--text-3);
}

.locked-tip {
  color: var(--amber);
}

/* 已过供餐时间的餐次 → 去评价 */
.review-link {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  margin-top: 10px;
  padding: 9px 12px;
  border: 1px dashed var(--brand-soft-border, var(--line));
  border-radius: 12px;
  background: var(--brand-softer, var(--brand-soft));
  color: var(--brand-dark);
  font-size: 12px;
  font-weight: 600;
  font-family: inherit;
  transition: transform 0.16s ease;
}

.review-link:active {
  transform: scale(0.985);
}

.review-link .chev {
  margin-left: auto;
  display: grid;
  place-items: center;
}

.action-bar {
  justify-content: space-between;
}

.action-summary {
  display: flex;
  align-items: center;
  gap: 8px;
}

.strong {
  font-size: 18px;
  font-weight: 800;
  color: var(--text);
}
</style>
