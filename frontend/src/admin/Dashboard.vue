<script setup>
import { computed, onMounted, ref } from 'vue'
import { NCard, NProgress, NSkeleton, NTag } from 'naive-ui'
import ChartBox from './ChartBox.vue'
import DateRangeSwitch from './DateRangeSwitch.vue'
import { api } from '../api/client'
import { MEAL_LABELS, addDays, rangeOf, todayISO, weekdayLabel } from '../utils/date'

const loading = ref(true)
const overview = ref(null)
const trend = ref([])
const trendRange = ref('week')

const today = todayISO()
const tomorrow = addDays(today, 1)

const stats = computed(() => {
  const data = overview.value
  if (!data) return []
  const span = data.range || rangeOf(trendRange.value)
  const spanText = `${span.start} ~ ${span.end}`
  return [
    {
      label: '今日就餐',
      value: data.today.total,
      unit: '人',
      foot: `早 ${data.today.meals.breakfast} · 午 ${data.today.meals.lunch} · 晚 ${data.today.meals.dinner}`,
    },
    {
      label: '明日就餐',
      value: data.tomorrow.total,
      unit: '人',
      foot: `早 ${data.tomorrow.meals.breakfast} · 午 ${data.tomorrow.meals.lunch} · 晚 ${data.tomorrow.meals.dinner}`,
    },
    {
      label: '区间预约人次',
      value: data.reservations.total_range,
      unit: '人次',
      foot: `日均 ${data.reservations.avg_per_day} · ${spanText}`,
    },
    {
      label: '区间评价',
      value: data.reviews.count_range,
      unit: '条',
      foot: `平均 ${data.reviews.avg_range} 分`,
    },
    {
      label: '区间反馈',
      value: data.feedback.total_range,
      unit: '条',
      foot: `待处理 ${data.feedback.pending} 条`,
    },
    {
      label: '菜单完整度',
      value: data.menus.complete,
      unit: `/ ${data.menus.total} 餐`,
      foot: data.menus.missing.length ? '有缺口，去菜单管理补齐' : '本周菜单已排满',
    },
  ]
})

const trendOption = computed(() => {
  const series = trend.value
  const meals = [
    { key: 'breakfast', name: '早餐', color: '#f0a33c' },
    { key: 'lunch', name: '午餐', color: '#1f6feb' },
    { key: 'dinner', name: '晚餐', color: '#7b61ff' },
  ]
  return {
    tooltip: { trigger: 'axis' },
    legend: { right: 0, top: 0, icon: 'roundRect', itemWidth: 10, itemHeight: 10 },
    grid: { left: 8, right: 12, top: 42, bottom: 6, containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: series.map((day) => `${day.date.slice(5)} ${day.label}`),
      axisLine: { lineStyle: { color: '#e6ebf3' } },
      axisLabel: { color: '#93a1b5', fontSize: 11 },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#f1f4f9' } },
      axisLabel: { color: '#93a1b5', fontSize: 11 },
    },
    series: meals.map((meal) => ({
      name: meal.name,
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 5,
      showSymbol: false,
      lineStyle: { width: 2.4, color: meal.color },
      itemStyle: { color: meal.color },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: `${meal.color}33` },
            { offset: 1, color: `${meal.color}00` },
          ],
        },
      },
      data: series.map((day) => day.meals[meal.key]),
    })),
  }
})

const todayOption = computed(() => {
  const data = overview.value
  const rows = data
    ? [
        { name: '早餐', value: data.today.meals.breakfast, itemStyle: { color: '#f0a33c' } },
        { name: '午餐', value: data.today.meals.lunch, itemStyle: { color: '#1f6feb' } },
        { name: '晚餐', value: data.today.meals.dinner, itemStyle: { color: '#7b61ff' } },
      ]
    : []
  return {
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, icon: 'circle', itemWidth: 9, itemHeight: 9 },
    series: [
      {
        type: 'pie',
        radius: ['52%', '74%'],
        center: ['50%', '44%'],
        avoidLabelOverlap: true,
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        data: rows,
      },
    ],
  }
})

const weekOption = computed(() => {
  const days = overview.value?.week.days || []
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 8, right: 12, top: 24, bottom: 6, containLabel: true },
    xAxis: {
      type: 'category',
      data: days.map((day) => day.label),
      axisLine: { lineStyle: { color: '#e6ebf3' } },
      axisLabel: { color: '#93a1b5', fontSize: 11 },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#f1f4f9' } },
      axisLabel: { color: '#93a1b5', fontSize: 11 },
    },
    series: [
      {
        type: 'bar',
        barWidth: 22,
        itemStyle: {
          borderRadius: [6, 6, 0, 0],
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: '#4aa3ff' },
              { offset: 1, color: '#1f6feb' },
            ],
          },
        },
        data: days.map((day) => day.total),
      },
    ],
  }
})

const reviewOption = computed(() => {
  const dist = overview.value?.reviews.distribution || []
  const colors = ['#0d7a49', '#3ea36b', '#f0a33c', '#e8823a', '#d64545']
  const labels = ['很差', '一般', '良好', '很好', '非常好']
  const total = dist.reduce((sum, item) => sum + item.count, 0)
  return {
    tooltip: { trigger: 'item' },
    grid: { left: 8, right: 44, top: 16, bottom: 12, containLabel: true },
    xAxis: { type: 'value', splitLine: { lineStyle: { color: '#f1f4f9' } }, axisLabel: { color: '#93a1b5' } },
    yAxis: {
      type: 'category',
      data: dist.map((item) => labels[item.rating - 1]),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#5b6a80', fontSize: 12 },
    },
    series: [
      {
        type: 'bar',
        barWidth: 16,
        itemStyle: { borderRadius: [0, 8, 8, 0] },
        label: {
          show: true,
          position: 'right',
          color: '#7d8ba1',
          fontSize: 11,
          formatter: (item) => {
            const count = item.value
            const percent = total ? Math.round((count / total) * 100) : 0
            return `${count} 条 ${percent}%`
          },
        },
        data: dist.map((item, index) => ({ value: item.count, itemStyle: { color: colors[index] } })),
      },
    ],
  }
})

const missingMenus = computed(() => overview.value?.menus.missing || [])
const recentFeedback = computed(() => overview.value?.feedback.recent || [])
const ranking = computed(() => overview.value?.votes.ranking || [])
const maxVotes = computed(() => Math.max(1, ...ranking.value.map((item) => item.votes)))
const tomorrowMenu = computed(() => overview.value?.tomorrow_menu || null)

const CATEGORY_LABELS = {
  taste: '口味咸淡',
  oil: '太油',
  fresh: '食材新鲜度',
  hygiene: '卫生',
  tableware: '餐具',
  other: '其他',
}

async function load() {
  loading.value = true
  try {
    const span = rangeOf(trendRange.value)
    const [overviewData, trendData] = await Promise.all([
      api.get('/stats/overview', { start: span.start, end: span.end }, 'admin'),
      api.get('/stats/trend', { start: span.start, end: span.end }, 'admin'),
    ])
    overview.value = overviewData
    trend.value = trendData.series || []
  } finally {
    loading.value = false
  }
}

async function changeTrend({ start, end }) {
  const [overviewData, trendData] = await Promise.all([
    api.get('/stats/overview', { start, end }, 'admin'),
    api.get('/stats/trend', { start, end }, 'admin'),
  ])
  overview.value = overviewData
  trend.value = trendData.series || []
}

onMounted(load)
</script>

<template>
  <div class="admin-page">
    <div class="page-head">
      <div>
        <h2>数据概览</h2>
        <p>预约、评价、反馈与投票的汇总情况，右上角可切换统计区间</p>
      </div>
      <div class="page-actions">
        <DateRangeSwitch v-model="trendRange" :options="['today', 'week', 'month']" size="small" @change="changeTrend" />
        <n-tag :bordered="false" type="info" round>{{ today }} {{ weekdayLabel(today) }}</n-tag>
      </div>
    </div>

    <n-skeleton v-if="loading" height="120px" :sharp="false" />
    <div v-else class="stat-grid">
      <div v-for="item in stats" :key="item.label" class="stat">
        <div class="stat-label">{{ item.label }}</div>
        <div class="stat-value">{{ item.value }}<small>{{ item.unit }}</small></div>
        <div class="stat-foot">{{ item.foot }}</div>
      </div>
    </div>

    <n-card :bordered="false" class="panel">
      <template #header>
        <div class="panel-head">
          <div class="panel-title"><i />预约趋势 <span class="panel-sub">按餐次统计就餐人数</span></div>
        </div>
      </template>
      <ChartBox :option="trendOption" height="280px" />
    </n-card>

    <div class="two-col">
      <n-card :bordered="false">
        <template #header>
          <div class="panel-title"><i />今日三餐占比</div>
        </template>
        <ChartBox :option="todayOption" height="240px" />
      </n-card>

      <n-card :bordered="false">
        <template #header>
          <div class="panel-title"><i />本周各日就餐人数</div>
        </template>
        <ChartBox :option="weekOption" height="240px" />
      </n-card>
    </div>

    <div class="two-col">
      <n-card :bordered="false" class="stretch-card">
        <template #header>
          <div class="panel-title"><i />区间评价分布 <span class="panel-sub">{{ (overview?.range?.start || '') }} ~ {{ (overview?.range?.end || '') }}</span></div>
        </template>
        <ChartBox :option="reviewOption" height="100%" class="fill-chart" />
      </n-card>

      <n-card :bordered="false" class="stretch-card">
        <template #header>
          <div class="panel-head">
            <div class="panel-title"><i />区间最爱菜排行</div>
            <span class="panel-sub">{{ overview?.votes.total || 0 }} 票</span>
          </div>
        </template>
        <div v-if="!ranking.length" class="empty-box">这个区间还没有人投票</div>
        <div v-else class="rank-list">
          <div v-for="(row, index) in ranking" :key="row.dish_name" class="rank-row">
            <span class="rank-no" :class="{ top: index === 0 }">{{ index + 1 }}</span>
            <span class="rank-name" :title="row.dish_name">{{ row.dish_name }}</span>
            <n-progress
              type="line"
              :percentage="Math.round((row.votes / maxVotes) * 100)"
              :show-indicator="false"
              :height="6"
              class="rank-bar"
              color="#1f6feb"
              rail-color="#eef3fb"
            />
            <span class="rank-value">{{ row.votes }} 票</span>
          </div>
        </div>
      </n-card>
    </div>

    <div class="two-col">
      <n-card :bordered="false">
        <template #header>
          <div class="panel-head">
            <div class="panel-title"><i />明日菜单</div>
            <span class="panel-sub">{{ tomorrowMenu?.date || tomorrow }} {{ tomorrowMenu?.weekday || '' }}</span>
          </div>
        </template>
        <n-skeleton v-if="loading" text :repeat="3" />
        <div v-else-if="tomorrowMenu?.is_weekend" class="empty-box">
          明天是{{ tomorrowMenu.weekday }}，食堂周末不供餐
        </div>
        <div v-else-if="!tomorrowMenu?.ready" class="empty-box warn-box">
          <p class="warn-title">明天还有餐次没排菜单</p>
          <p class="muted tiny">去「菜单管理」补齐后再来看这里</p>
        </div>
        <div v-else class="tm-menu">
          <div v-for="meal in tomorrowMenu.meals" :key="meal.meal" class="tm-meal">
            <div class="tm-meal-head">
              <span class="tm-meal-name">{{ meal.label }}</span>
              <span class="muted tiny">{{ meal.dishes.length }} 道</span>
            </div>
            <div class="tm-dishes">
              <span v-for="dish in meal.dishes" :key="dish.name" class="tm-dish">
                {{ dish.name }}
                <i>{{ dish.type }}</i>
              </span>
            </div>
          </div>
        </div>
      </n-card>

      <n-card :bordered="false">
        <template #header>
          <div class="panel-head">
            <div class="panel-title"><i />最新反馈</div>
            <span class="panel-sub">匿名</span>
          </div>
        </template>
        <div v-if="!recentFeedback.length" class="empty-box">暂无反馈</div>
        <div v-for="row in recentFeedback" :key="row.id" class="feedback-row">
          <div class="feedback-top">
            <span class="chip">{{ CATEGORY_LABELS[row.category] || '其他' }}</span>
            <span class="muted tiny">{{ (row.created_at || '').replace('T', ' ').slice(0, 16) }}</span>
            <span class="chip" :class="row.handled ? 'ok' : 'warn'">{{ row.handled ? '已处理' : '待处理' }}</span>
          </div>
          <p class="feedback-text">{{ row.content }}</p>
        </div>
      </n-card>
    </div>
  </div>
</template>

<style scoped>
.two-col {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 16px;
  align-items: stretch;
}

.panel {
  border-radius: 12px;
}

/* 让图表卡片内容区自动占满剩余高度（ChartBox 里 echarts 容器 100% 高） */
.stretch-card :deep(.n-card__content) {
  display: flex;
  flex-direction: column;
}

.fill-chart {
  flex: 1;
  min-height: 220px;
}

/* ── 最爱菜排行：菜名不压缩 ───────────────── */
.rank-list {
  display: flex;
  flex-direction: column;
  justify-content: space-evenly;
  min-height: 220px;
}

.rank-row {
  display: grid;
  grid-template-columns: 24px minmax(96px, auto) 1fr 52px;
  align-items: center;
  gap: 10px;
  padding: 6px 0;
}

.rank-name {
  font-size: 13px;
  color: #1d2739;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rank-bar {
  width: 100%;
}

.rank-value {
  font-size: 12px;
  color: #7d8ba1;
  text-align: right;
  white-space: nowrap;
}

/* ── 明日菜单 ─────────────────────────────── */
.tm-menu {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tm-meal {
  padding: 10px 12px;
  background: #f8f9fb;
  border-radius: 10px;
}

.tm-meal-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 8px;
}

.tm-meal-name {
  font-size: 13px;
  font-weight: 600;
  color: #111827;
}

.tm-dishes {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tm-dish {
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
  padding: 3px 9px;
  background: #fff;
  border: 1px solid #e9eef5;
  border-radius: 7px;
  font-size: 12.5px;
  color: #2b3441;
}

.tm-dish i {
  font-style: normal;
  font-size: 10.5px;
  color: #a3abb8;
}

.warn-box .warn-title {
  margin: 0 0 4px;
  font-size: 13.5px;
  font-weight: 600;
  color: #b07a17;
}

.feedback-row {
  padding: 10px 0;
  border-bottom: 1px dashed #eef1f6;
}

.feedback-row:last-child {
  border-bottom: none;
}

.feedback-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.feedback-text {
  margin: 0;
  font-size: 13px;
  color: #46536b;
  line-height: 1.6;
}
</style>
