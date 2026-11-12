<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { NButton, NCard, NIcon, NSkeleton, NTag, useMessage } from 'naive-ui'
import { DownloadOutline } from '@vicons/ionicons5'
import ChartBox from './ChartBox.vue'
import DateRangeSwitch from './DateRangeSwitch.vue'
import { api, downloadBlob } from '../api/client'
import { MEAL_LABELS, MEALS, RANGE_LABELS, formatDateTime, rangeOf, todayISO, weekdayLabel } from '../utils/date'

const message = useMessage()

const loading = ref(true)
const dayLoading = ref(false)
const summary = ref(null)
const dayDetail = ref(null)
const rangeKey = ref('week')
const customRange = ref(null)
const selectedDay = ref(todayISO())
const exporting = ref(false)

const range = computed(() => customRange.value || rangeOf(rangeKey.value === 'custom' ? 'week' : rangeKey.value))
const rangeStart = computed(() => range.value.start)
const rangeEnd = computed(() => range.value.end)
const rangeText = computed(() => `${rangeStart.value} ~ ${rangeEnd.value}`)

const MEAL_DOTS = { breakfast: 'amber', lunch: 'green', dinner: 'violet' }

const stats = computed(() => {
  const data = summary.value
  if (!data) return []
  const low = (data.distribution || [])
    .filter((item) => item.rating <= 2)
    .reduce((sum, item) => sum + item.count, 0)
  return [
    { label: '评价总数', value: data.total, unit: '条', foot: rangeText.value },
    { label: '平均分', value: data.avg, unit: '/ 5', foot: '满分 5 分' },
    { label: '好评率', value: data.good_rate, unit: '%', foot: '3 分及以上占比' },
    { label: '低分评价', value: low, unit: '条', foot: '1~2 分，需要重点关注' },
  ]
})

/** 有数据的日期（外加今天），用于左侧日期列表 */
const dayList = computed(() => {
  const series = summary.value?.series || []
  const today = todayISO()
  return series
    .filter((item) => item.count > 0 || item.date === today)
    .map((item) => ({ ...item, weekday: weekdayLabel(item.date) }))
    .sort((a, b) => b.date.localeCompare(a.date))
})

const distOption = computed(() => {
  const dist = summary.value?.distribution || []
  const colors = { 5: '#0d7a49', 4: '#3ea36b', 3: '#f0a33c', 2: '#e8823a', 1: '#d64545' }
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 8, right: 12, top: 12, bottom: 6, containLabel: true },
    xAxis: {
      type: 'category',
      data: dist.map((item) => `${item.label}(${item.rating}分)`),
      axisLine: { lineStyle: { color: '#e6ebf3' } },
      axisTick: { show: false },
      axisLabel: { color: '#7d8ba1', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#f1f4f9' } },
      axisLabel: { color: '#93a1b5', fontSize: 11 },
    },
    series: [
      {
        type: 'bar',
        barWidth: 26,
        itemStyle: { borderRadius: [6, 6, 0, 0] },
        label: { show: true, position: 'top', color: '#7d8ba1', fontSize: 11 },
        data: dist.map((item) => ({ value: item.count, itemStyle: { color: colors[item.rating] } })),
      },
    ],
  }
})

/** 每天平均分趋势（只看今天及以前，避免未来日期把折线拉成 0） */
const trendOption = computed(() => {
  const today = todayISO()
  const series = (summary.value?.series || []).filter((item) => item.date <= today)
  return {
    tooltip: {
      trigger: 'axis',
      valueFormatter: (value) => (value === null || value === undefined ? '—' : value),
    },
    legend: { right: 0, top: 0, icon: 'roundRect', itemWidth: 10, itemHeight: 10 },
    grid: { left: 8, right: 12, top: 40, bottom: 6, containLabel: true },
    xAxis: {
      type: 'category',
      data: series.map((item) => item.date.slice(5)),
      axisLine: { lineStyle: { color: '#e6ebf3' } },
      axisTick: { show: false },
      axisLabel: { color: '#93a1b5', fontSize: 11 },
    },
    yAxis: [
      {
        type: 'value',
        name: '条',
        nameTextStyle: { color: '#93a1b5', fontSize: 11 },
        splitLine: { lineStyle: { color: '#f1f4f9' } },
        axisLabel: { color: '#93a1b5', fontSize: 11 },
      },
      {
        type: 'value',
        name: '分',
        min: 0,
        max: 5,
        nameTextStyle: { color: '#93a1b5', fontSize: 11 },
        splitLine: { show: false },
        axisLabel: { color: '#93a1b5', fontSize: 11 },
      },
    ],
    series: [
      {
        name: '评价数',
        type: 'bar',
        barWidth: 16,
        itemStyle: { borderRadius: [6, 6, 0, 0], color: '#9cc4fb' },
        data: series.map((item) => item.count),
      },
      {
        name: '平均分',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        showSymbol: true,
        symbolSize: 6,
        connectNulls: false,
        lineStyle: { width: 2.4, color: '#1f6feb' },
        itemStyle: { color: '#1f6feb' },
        data: series.map((item) => item.avg),
      },
    ],
  }
})

const reasonGroups = computed(() => {
  const reasons = summary.value?.reasons || {}
  return [
    { title: '口味', items: reasons.taste || [] },
    { title: '搭配', items: reasons.pairing || [] },
    { title: '分量', items: reasons.portion || [] },
  ]
})

const dayMeals = computed(() =>
  MEALS.map((meal) => ({
    meal,
    label: MEAL_LABELS[meal],
    dot: MEAL_DOTS[meal],
    ...(dayDetail.value?.meals?.[meal] || { count: 0, avg: null, low: 0, comments: [], dishes: [], distribution: [] }),
  })),
)

const ratingType = { 5: 'success', 4: 'success', 3: 'warning', 2: 'error', 1: 'error' }

function scoreClass(score) {
  if (!score) return 'none'
  if (score >= 4) return 'good'
  if (score >= 3) return 'mid'
  return 'low'
}

async function loadSummary() {
  loading.value = true
  try {
    const data = await api.get('/reviews/summary', { start: rangeStart.value, end: rangeEnd.value }, 'admin')
    summary.value = data
    // 默认选中：今天有评价就选今天，否则选最近一个有评价的日期
    const todayWithData = data.series?.some((item) => item.date === todayISO() && item.count > 0)
    if (todayWithData) {
      selectedDay.value = todayISO()
    } else {
      const latest = [...(data.series || [])].reverse().find((item) => item.count > 0)
      selectedDay.value = latest?.date || todayISO()
    }
  } catch (error) {
    message.error(error.message)
  } finally {
    loading.value = false
  }
}

async function loadDay(day) {
  if (!day) return
  dayLoading.value = true
  try {
    dayDetail.value = await api.get(`/reviews/day/${day}`, undefined, 'admin')
  } catch (error) {
    message.error(error.message)
  } finally {
    dayLoading.value = false
  }
}

async function changeRange({ key, start, end }) {
  rangeKey.value = key
  customRange.value = key === 'custom' ? { start, end } : null
  await loadSummary()
  await loadDay(selectedDay.value)
}

async function exportExcel() {
  exporting.value = true
  try {
    const blob = await api.blob('/reviews/export', { start: rangeStart.value, end: rangeEnd.value }, 'admin')
    downloadBlob(blob, `菜品评价_${rangeStart.value}_${rangeEnd.value}.xlsx`)
    message.success('已导出 Excel')
  } catch (error) {
    message.error(error.message)
  } finally {
    exporting.value = false
  }
}

watch(selectedDay, (day) => loadDay(day))

onMounted(async () => {
  await loadSummary()
  await loadDay(selectedDay.value)
})
</script>

<template>
  <div class="admin-page">
    <div class="page-head">
      <div>
        <h2>菜品评价</h2>
        <p>按每天的早餐 / 午餐 / 晚餐查看员工评价，同时能看到当天这三餐的菜单</p>
      </div>
      <div class="page-actions">
        <DateRangeSwitch v-model="rangeKey" @change="changeRange" />
        <n-button size="small" type="primary" :loading="exporting" @click="exportExcel">
          <template #icon><n-icon :component="DownloadOutline" /></template>
          导出 Excel
        </n-button>
      </div>
    </div>

    <n-skeleton v-if="loading && !summary" height="110px" :sharp="false" />
    <div v-else class="stat-grid">
      <div v-for="item in stats" :key="item.label" class="stat">
        <div class="stat-label">{{ item.label }}</div>
        <div class="stat-value">{{ item.value }}<small>{{ item.unit }}</small></div>
        <div class="stat-foot">{{ item.foot }}</div>
      </div>
    </div>

    <div class="two-col">
      <n-card :bordered="false">
        <template #header>
          <div class="panel-title"><i />评分分布</div>
        </template>
        <ChartBox :option="distOption" height="230px" />
      </n-card>
      <n-card :bordered="false">
        <template #header>
          <div class="panel-title"><i />每天平均分趋势 <span class="panel-sub">柱状为数量，折线为平均分</span></div>
        </template>
        <ChartBox :option="trendOption" height="230px" />
      </n-card>
    </div>

    <!-- 按天 × 三餐 -->
    <section class="day-layout">
      <aside class="day-list">
        <div class="day-list-head">日期</div>
        <button
          v-for="day in dayList"
          :key="day.date"
          type="button"
          class="day-item"
          :class="{ active: day.date === selectedDay }"
          @click="selectedDay = day.date"
        >
          <span class="di-date">{{ day.date.slice(5) }}</span>
          <span class="di-week">{{ day.weekday }}</span>
          <span class="di-score" :class="scoreClass(day.avg)">
            <template v-if="day.count">{{ day.avg ?? '—' }} 分</template>
            <template v-else>无评价</template>
            <i v-if="day.count">{{ day.count }} 条</i>
          </span>
        </button>
        <div v-if="!dayList.length" class="day-list-empty">这个区间还没有评价</div>
      </aside>

      <div class="day-panel">
        <header class="day-panel-head">
          <div class="dph-title">
            <strong>{{ selectedDay }}</strong>
            <span>{{ weekdayLabel(selectedDay) }}</span>
          </div>
          <div class="dph-meta">
            <span class="dph-avg" :class="scoreClass(dayDetail?.avg)">
              {{ dayDetail?.avg ? `${dayDetail.avg} 分` : '暂无评分' }}
            </span>
            <span class="muted tiny">{{ dayDetail?.total || 0 }} 条评价 · 共 3 餐</span>
          </div>
        </header>

        <n-skeleton v-if="dayLoading" text :repeat="6" />
        <div v-else class="meal-grid">
          <article v-for="meal in dayMeals" :key="meal.meal" class="meal-card">
            <header class="meal-card-head">
              <span class="meal-name"><i class="dot" :class="meal.dot" />{{ meal.label }}</span>
              <span class="meal-score" :class="scoreClass(meal.avg)">
                <template v-if="meal.count">{{ meal.avg }} 分 · {{ meal.count }} 条</template>
                <template v-else>暂无评价</template>
              </span>
            </header>

            <div class="meal-menu">
              <span v-if="meal.dishes?.length" class="dish-list">
                <span v-for="dish in meal.dishes" :key="dish.name" class="dish-chip">
                  {{ dish.name }}
                  <i>{{ dish.type }}</i>
                </span>
              </span>
              <span v-else class="meal-menu-empty">当天这一餐没有菜单</span>
            </div>

            <div v-if="meal.comments?.length" class="comment-list">
              <div v-for="comment in meal.comments.slice(0, 5)" :key="comment.id" class="comment">
                <n-tag size="small" :type="ratingType[comment.rating]" :bordered="false" round>
                  {{ comment.rating_label }}
                </n-tag>
                <div class="comment-body">
                  <p v-if="comment.comment" class="comment-text">{{ comment.comment }}</p>
                  <div v-if="comment.taste || comment.pairing || comment.portion" class="comment-reasons">
                    <span v-if="comment.taste" class="chip warn">口味：{{ comment.taste }}</span>
                    <span v-if="comment.pairing" class="chip warn">搭配：{{ comment.pairing }}</span>
                    <span v-if="comment.portion" class="chip warn">分量：{{ comment.portion }}</span>
                  </div>
                  <span class="muted tiny">{{ formatDateTime(comment.created_at) }}</span>
                </div>
              </div>
              <div v-if="meal.comments.length > 5" class="muted tiny comment-more">
                还有 {{ meal.comments.length - 5 }} 条未展示
              </div>
            </div>
            <div v-else class="meal-empty">这一餐还没有评价</div>
          </article>
        </div>
      </div>
    </section>

    <n-card :bordered="false">
      <template #header>
        <div class="panel-title"><i />不满意原因统计 <span class="panel-sub">{{ rangeText }}</span></div>
      </template>
      <div class="reason-grid">
        <div v-for="group in reasonGroups" :key="group.title" class="reason-group">
          <div class="reason-title">{{ group.title }}</div>
          <div v-if="group.items.length" class="reason-tags">
            <span v-for="item in group.items" :key="item.label" class="chip">
              {{ item.label }} · {{ item.count }}
            </span>
          </div>
          <div v-else class="muted tiny">暂无</div>
        </div>
      </div>
    </n-card>
  </div>
</template>

<style scoped>
.two-col {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
  gap: 16px;
}

/* ── 按天 + 三餐 ─────────────────────────── */
.day-layout {
  display: grid;
  grid-template-columns: 208px minmax(0, 1fr);
  gap: 16px;
}

.day-list {
  background: #fff;
  border: 1px solid #eceef2;
  border-radius: 12px;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 3px;
  max-height: 560px;
  overflow-y: auto;
}

.day-list-head {
  font-size: 11.5px;
  color: #9aa3af;
  padding: 6px 8px 8px;
  letter-spacing: 0.5px;
}

.day-item {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border: none;
  border-radius: 8px;
  background: transparent;
  cursor: pointer;
  text-align: left;
  transition: background 0.15s;
}

.day-item:hover {
  background: #f7f8fa;
}

.day-item.active {
  background: #eef1f5;
}

.di-date {
  font-size: 13px;
  color: #111827;
  font-weight: 600;
}

.di-week {
  font-size: 11.5px;
  color: #9aa3af;
}

.day-item.active .di-week {
  color: #6b7280;
}

.di-score {
  display: inline-flex;
  flex-direction: column;
  align-items: flex-end;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.3;
}

.di-score i {
  font-style: normal;
  font-weight: 400;
  font-size: 10.5px;
  color: #9aa3af;
}

.di-score.good {
  color: #0d7a49;
}

.di-score.mid {
  color: #b9770e;
}

.di-score.low {
  color: #c02c2c;
}

.di-score.none {
  color: #b6bfcb;
  font-weight: 400;
}

.day-list-empty {
  padding: 18px 8px;
  font-size: 12px;
  color: #b6bfcb;
  text-align: center;
}

.day-panel {
  background: #fff;
  border: 1px solid #eceef2;
  border-radius: 12px;
  padding: 14px 16px 16px;
}

.day-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f1f3f6;
  margin-bottom: 14px;
}

.dph-title {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.dph-title strong {
  font-size: 15px;
  color: #111827;
  letter-spacing: 0.3px;
}

.dph-title span {
  font-size: 12px;
  color: #9aa3af;
}

.dph-meta {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.dph-avg {
  font-size: 15px;
  font-weight: 700;
}

.dph-avg.good {
  color: #0d7a49;
}

.dph-avg.mid {
  color: #b9770e;
}

.dph-avg.low {
  color: #c02c2c;
}

.dph-avg.none {
  color: #b6bfcb;
  font-weight: 500;
  font-size: 13px;
}

.meal-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 12px;
}

.meal-card {
  border: 1px solid #f0f2f5;
  border-radius: 10px;
  padding: 12px 12px 14px;
  background: #fcfcfd;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.meal-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.meal-name {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #111827;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex: none;
}

.dot.amber {
  background: #f0a94c;
}

.dot.green {
  background: #34a06a;
}

.dot.violet {
  background: #7c74e8;
}

.meal-score {
  font-size: 12px;
  font-weight: 600;
}

.meal-score.good {
  color: #0d7a49;
}

.meal-score.mid {
  color: #b9770e;
}

.meal-score.low {
  color: #c02c2c;
}

.meal-score.none {
  color: #b6bfcb;
  font-weight: 400;
}

.meal-menu {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  padding: 8px;
  background: #f7f9fc;
  border-radius: 8px;
}

.dish-list {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.dish-chip {
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
  padding: 2px 7px;
  border-radius: 6px;
  background: #fff;
  border: 1px solid #e9eef5;
  font-size: 12px;
  color: #2b3441;
}

.dish-chip i {
  font-style: normal;
  font-size: 10px;
  color: #a3abb8;
}

.meal-menu-empty {
  font-size: 11.5px;
  color: #b6bfcb;
}

.comment-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.comment {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}

.comment-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.comment-text {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.6;
  color: #33404f;
}

.comment-reasons {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.comment-more {
  text-align: right;
}

.meal-empty {
  font-size: 12px;
  color: #b6bfcb;
  padding: 8px 0 2px;
}

.reason-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 8px 24px;
}

.reason-group {
  padding: 6px 0;
}

.reason-title {
  font-size: 13px;
  font-weight: 600;
  color: #33404f;
  margin-bottom: 8px;
}

.reason-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

@media (max-width: 900px) {
  .day-layout {
    grid-template-columns: 1fr;
  }

  .day-list {
    max-height: 240px;
  }
}
</style>
