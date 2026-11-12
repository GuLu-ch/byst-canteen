<script setup>
import { computed, h, onMounted, ref } from 'vue'
import { NCard, NProgress, NSelect, NSkeleton, NTag, useMessage } from 'naive-ui'
import ChartBox from './ChartBox.vue'
import DateRangeSwitch from './DateRangeSwitch.vue'
import { api } from '../api/client'
import { rangeOf, todayISO, weekStartOf } from '../utils/date'

const message = useMessage()

const loading = ref(true)
const weeks = ref([])
const weekStart = ref(weekStartOf(todayISO()))
const stats = ref(null)

// 快捷区间（今日 / 本周 / 最近30天 / 自定义）与周选择共用一个结果
const rangeKey = ref('week')
const customRange = ref(null)

const range = computed(() => customRange.value || rangeOf(rangeKey.value === 'custom' ? 'week' : rangeKey.value))

const weekOptions = computed(() =>
  weeks.value.map((week) => ({ label: `${week.slice(5)} 起的一周`, value: week })),
)

const spanText = computed(() =>
  stats.value?.mode === 'week'
    ? `${stats.value.week_start} ~ ${stats.value.week_end}`
    : `${stats.value?.start || ''} ~ ${stats.value?.end || ''}`,
)

const statCards = computed(() => {
  const data = stats.value
  if (!data) return []
  const top = data.ranking?.[0]
  return [
    { label: '投票人数', value: data.total_votes, unit: '人', foot: `共 ${data.total_picks} 票` },
    { label: '在职员工', value: data.eligible, unit: '人', foot: '可参与投票的人数' },
    { label: '参与率', value: data.participation, unit: '%', foot: '投票人数 / 在职员工' },
    { label: '最爱菜', value: top ? top.dish_name : '—', unit: '', foot: top ? `${top.votes} 票` : '暂无投票' },
  ]
})

const barOption = computed(() => {
  const ranking = (stats.value?.ranking || []).slice(0, 8).reverse()
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 8, right: 28, top: 12, bottom: 6, containLabel: true },
    xAxis: { type: 'value', splitLine: { lineStyle: { color: '#f1f4f9' } }, axisLabel: { color: '#93a1b5' } },
    yAxis: {
      type: 'category',
      data: ranking.map((row) => row.dish_name),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#5b6a80', fontSize: 12 },
    },
    series: [
      {
        type: 'bar',
        barWidth: 16,
        label: { show: true, position: 'right', color: '#7d8ba1', fontSize: 11 },
        itemStyle: {
          borderRadius: [0, 8, 8, 0],
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 1,
            y2: 0,
            colorStops: [
              { offset: 0, color: '#1f6feb' },
              { offset: 1, color: '#63a9ff' },
            ],
          },
        },
        data: ranking.map((row) => row.votes),
      },
    ],
  }
})

const ranking = computed(() => stats.value?.ranking || [])

const columns = [
  {
    title: '名次',
    key: 'rank',
    width: 80,
    render: (row) => h('span', { class: row.rank <= 3 ? 'rank-no top' : 'rank-no' }, row.rank),
  },
  { title: '菜品', key: 'dish_name', render: (row) => h('span', { class: 'cell-strong' }, row.dish_name) },
  { title: '票数', key: 'votes', width: 100, align: 'center' },
  {
    title: '占比',
    key: 'percent',
    minWidth: 220,
    render: (row) =>
      h(NProgress, {
        type: 'line',
        percentage: Math.min(100, row.percent),
        height: 8,
        color: '#1f6feb',
        railColor: '#eef3fb',
        indicatorPlacement: 'right',
      }),
  },
]

async function loadWeeks() {
  const data = await api.get('/votes/weeks', undefined, 'admin')
  weeks.value = data.weeks || []
}

async function loadStats() {
  loading.value = true
  try {
    const params =
      rangeKey.value === 'custom' || customRange.value
        ? { start: range.value.start, end: range.value.end }
        : { week_start: weekStart.value }
    stats.value = await api.get('/votes/stats', params, 'admin')
  } catch (error) {
    message.error(error.message)
  } finally {
    loading.value = false
  }
}

async function changeWeek(value) {
  // 从周选择切换：清掉自定义区间，按周口径查询
  weekStart.value = value
  customRange.value = null
  rangeKey.value = 'week'
  await loadStats()
}

async function onRangeChange({ key, start, end }) {
  rangeKey.value = key
  if (key === 'custom') {
    customRange.value = { start, end }
  } else {
    customRange.value = null
    // 让周选择器跟随快捷区间（最近30天不对应单周，保持原值即可）
    if (key === 'today' || key === 'week') {
      weekStart.value = weekStartOf(range.value.start)
    }
  }
  await loadStats()
}

onMounted(async () => {
  await loadWeeks()
  await loadStats()
})
</script>

<template>
  <div class="admin-page">
    <div class="page-head">
      <div>
        <h2>最爱菜投票</h2>
        <p>「最喜欢的菜」投票结果，可按周查看，也可用快捷区间汇总</p>
      </div>
      <div class="page-actions">
        <DateRangeSwitch v-model="rangeKey" @change="onRangeChange" />
        <n-select
          :value="weekStart"
          :options="weekOptions"
          size="small"
          style="width: 150px"
          @update:value="changeWeek"
        />
      </div>
    </div>

    <n-skeleton v-if="loading && !stats" height="110px" :sharp="false" />
    <div v-else class="stat-grid">
      <div v-for="item in statCards" :key="item.label" class="stat">
        <div class="stat-label">{{ item.label }}</div>
        <div class="stat-value">{{ item.value }}<small>{{ item.unit }}</small></div>
        <div class="stat-foot">{{ item.foot }}</div>
      </div>
    </div>

    <div class="two-col">
      <n-card :bordered="false">
        <template #header>
          <div class="panel-head">
            <div class="panel-title"><i />投票排行</div>
            <span class="panel-sub">{{ spanText }}</span>
          </div>
        </template>
        <n-skeleton v-if="loading" text :repeat="6" />
        <template v-else>
          <n-data-table
            v-if="ranking.length"
            :columns="columns"
            :data="ranking"
            :bordered="false"
            size="small"
            :row-key="(row) => row.dish_name"
          />
          <div v-else class="empty-box">这个区间还没有人投票</div>
        </template>
      </n-card>

      <n-card :bordered="false">
        <template #header>
          <div class="panel-title"><i />前 8 名票数</div>
        </template>
        <ChartBox v-if="ranking.length" :option="barOption" height="280px" />
        <div v-else class="empty-box">暂无数据</div>
      </n-card>
    </div>
  </div>
</template>

<style scoped>
.two-col {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
  gap: 16px;
}
</style>
