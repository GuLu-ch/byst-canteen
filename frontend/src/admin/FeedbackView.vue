<script setup>
import { computed, h, onMounted, ref, watch } from 'vue'
import { NButton, NCard, NDataTable, NSelect, NSkeleton, NTag, useMessage } from 'naive-ui'
import { useRoute } from 'vue-router'
import ChartBox from './ChartBox.vue'
import DateRangeSwitch from './DateRangeSwitch.vue'
import { api } from '../api/client'
import { notifyFeedbackHandled } from '../stores/adminBadges'
import { rangeOf, todayISO } from '../utils/date'

const message = useMessage()

const loading = ref(true)
const stats = ref(null)
const rows = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const rangeKey = ref('week')
const customRange = ref(null)
const category = ref('')
const handled = ref('')

const route = useRoute()

const range = computed(() => customRange.value || rangeOf(rangeKey.value === 'custom' ? 'week' : rangeKey.value))
const rangeText = computed(() => `${range.value.start} ~ ${range.value.end}`)

const CATEGORY_LABELS = {
  taste: '口味咸淡',
  oil: '菜品太油',
  fresh: '食材新鲜度',
  hygiene: '卫生问题',
  tableware: '餐具问题',
  other: '其他建议',
}

const categoryOptions = [
  { label: '全部类型', value: '' },
  ...Object.entries(CATEGORY_LABELS).map(([value, label]) => ({ label, value })),
]

const handledOptions = [
  { label: '全部状态', value: '' },
  { label: '待处理', value: 'false' },
  { label: '已处理', value: 'true' },
]

const statCards = computed(() => {
  const data = stats.value
  if (!data) return []
  return [
    { label: '区间反馈', value: data.total, unit: '条', foot: rangeText.value },
    { label: '待处理', value: data.pending, unit: '条', foot: '处理完记得标记' },
    { label: '已处理', value: data.handled, unit: '条' },
    { label: '本周新增', value: data.this_week, unit: '条' },
  ]
})

const categoryOption = computed(() => {
  const data = stats.value?.by_category || []
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 8, right: 24, top: 10, bottom: 6, containLabel: true },
    xAxis: { type: 'value', splitLine: { lineStyle: { color: '#f1f4f9' } }, axisLabel: { color: '#93a1b5' } },
    yAxis: {
      type: 'category',
      data: data.map((item) => item.label),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#5b6a80' },
    },
    series: [
      {
        type: 'bar',
        barWidth: 14,
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
        data: data.map((item) => item.count),
      },
    ],
  }
})

const trendOption = computed(() => {
  const series = stats.value?.series || []
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 8, right: 16, top: 20, bottom: 6, containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: series.map((item) => item.date.slice(5)),
      axisLine: { lineStyle: { color: '#e6ebf3' } },
      axisTick: { show: false },
      axisLabel: { color: '#93a1b5', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#f1f4f9' } },
      axisLabel: { color: '#93a1b5', fontSize: 11 },
    },
    series: [
      {
        type: 'line',
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 2.4, color: '#1f6feb' },
        itemStyle: { color: '#1f6feb' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: '#1f6feb33' },
              { offset: 1, color: '#1f6feb00' },
            ],
          },
        },
        data: series.map((item) => item.count),
      },
    ],
  }
})

const columns = [
  {
    title: '内容',
    key: 'content',
    minWidth: 320,
    render: (row) =>
      h('div', null, [
        h('div', { style: 'display:flex;align-items:center;gap:8px;margin-bottom:4px' }, [
          h(NTag, { size: 'small', bordered: false, type: 'info', round: true }, { default: () => row.category_label }),
          h('span', { class: 'cell-sub' }, (row.created_at || '').replace('T', ' ').slice(0, 16)),
        ]),
        h('div', { style: 'font-size:13px;color:#33404f;line-height:1.6' }, row.content),
      ]),
  },
  { title: '日期', key: 'date', width: 120 },
  {
    title: '状态',
    key: 'handled',
    width: 100,
    render: (row) =>
      h(
        NTag,
        { size: 'small', bordered: false, round: true, type: row.handled ? 'success' : 'warning' },
        { default: () => (row.handled ? '已处理' : '待处理') },
      ),
  },
  {
    title: '操作',
    key: 'actions',
    width: 120,
    render: (row) =>
      row.handled
        ? h('span', { class: 'cell-sub' }, '已归档')
        : h(
            NButton,
            { size: 'tiny', type: 'primary', secondary: true, onClick: () => markHandled(row) },
            { default: () => '标记已处理' },
          ),
  },
]

const pagination = computed(() => ({
  page: page.value,
  pageSize: pageSize.value,
  itemCount: total.value,
  pageSizes: [10, 20, 50],
  prefix: () => `共 ${total.value} 条`,
  onUpdatePage: (value) => {
    page.value = value
    loadList()
  },
  onUpdatePageSize: (value) => {
    pageSize.value = value
    page.value = 1
    loadList()
  },
}))

/** n-data-table remote 分页时必须显式声明，否则分页器不出现/翻页无效 */
const remote = computed(() => true)

async function loadStats() {
  stats.value = await api.get(
    '/feedback/stats',
    { start: range.value.start, end: range.value.end },
    'admin',
  )
}

/** 看「待处理」时不限日期区间：否则早于本周的待处理反馈会被区间挡掉，导致小红点一直亮 */
const showAllPending = computed(() => handled.value === 'false')

async function loadList() {
  loading.value = true
  try {
    const params = {
      page: page.value,
      page_size: pageSize.value,
      category: category.value,
      handled: handled.value,
    }
    if (!showAllPending.value) {
      params.start = range.value.start
      params.end = range.value.end
    }
    const data = await api.get('/feedback', params, 'admin')
    rows.value = data.items
    total.value = data.total
  } catch (error) {
    message.error(error.message)
  } finally {
    loading.value = false
  }
}

function onRangeChange({ key, start, end }) {
  rangeKey.value = key
  customRange.value = key === 'custom' ? { start, end } : null
  reload()
}

async function reload() {
  page.value = 1
  await Promise.all([loadStats(), loadList()])
}

/** 标记为已处理：单向操作。小红点数量本地实时减一（归零立即消失），再向服务端核对 */
async function markHandled(row) {
  try {
    const result = await api.put(`/feedback/${row.id}/handled`, undefined, 'admin')
    row.handled = true
    notifyFeedbackHandled()
    await loadStats()
    // 处理完提示还剩多少待处理（含其他日期的），避免以为处理完了红点却还在
    const left = stats.value?.pending_all ?? 0
    if (left > 0) {
      message.success(`${result?.message || '已标记为已处理'}，还剩 ${left} 条待处理（可点这里查看全部待处理）`)
    } else {
      message.success('已全部处理完毕')
    }
  } catch (error) {
    message.error(error.message)
  }
}

/** 一键查看全部待处理（不限日期区间） */
function showPending() {
  handled.value = 'false'
  page.value = 1
  loadList()
}

function clearFilters() {
  category.value = ''
  handled.value = ''
  page.value = 1
  loadList()
}

onMounted(() => {
  // 支持从导航小红点直接进入「全部待处理」列表
  if (route.query.handled === 'false') handled.value = 'false'
  reload()
})
</script>

<template>
  <div class="admin-page">
    <div class="page-head">
      <div>
        <h2>意见反馈</h2>
        <p>员工匿名反馈，后台只看到内容与类型，看不到提交人（保护反馈真实度）</p>
      </div>
      <div class="page-actions">
        <button
          v-if="stats?.pending_all"
          type="button"
          class="pending-pill"
          :class="{ active: handled === 'false' }"
          @click="showPending"
        >
          待处理 {{ stats.pending_all }} 条
        </button>
        <DateRangeSwitch v-model="rangeKey" @change="onRangeChange" />
      </div>
    </div>

    <n-skeleton v-if="!stats" height="110px" :sharp="false" />
    <div v-else class="stat-grid">
      <div v-for="item in statCards" :key="item.label" class="stat">
        <div class="stat-label">{{ item.label }}</div>
        <div class="stat-value">{{ item.value }}<small>{{ item.unit }}</small></div>
        <div v-if="item.foot" class="stat-foot">{{ item.foot }}</div>
      </div>
    </div>

    <div class="two-col">
      <n-card :bordered="false">
        <template #header>
          <div class="panel-title"><i />反馈类型分布</div>
        </template>
        <ChartBox :option="categoryOption" height="240px" />
      </n-card>
      <n-card :bordered="false">
        <template #header>
          <div class="panel-title"><i />反馈趋势</div>
        </template>
        <ChartBox :option="trendOption" height="240px" />
      </n-card>
    </div>

    <n-card :bordered="false">
      <template #header>
        <div class="panel-head">
          <div class="panel-title">
            <i />反馈列表
            <span class="panel-sub">
              共 {{ total }} 条<template v-if="showAllPending">（待处理不限日期区间）</template>
            </span>
          </div>
          <div class="toolbar">
            <n-select
              v-model:value="category"
              :options="categoryOptions"
              size="small"
              style="width: 140px"
              @update:value="loadList"
            />
            <n-select
              v-model:value="handled"
              :options="handledOptions"
              size="small"
              style="width: 120px"
              @update:value="loadList"
            />
            <n-button size="small" quaternary @click="clearFilters">重置</n-button>
          </div>
        </div>
      </template>

      <n-skeleton v-if="loading" text :repeat="5" />
      <template v-else>
        <n-data-table
          :columns="columns"
          :data="rows"
          :bordered="false"
          size="small"
          :row-key="(row) => row.id"
          remote
          :pagination="pagination"
        />
        <div v-if="!rows.length" class="empty-box">没有符合条件的反馈</div>
      </template>
    </n-card>
  </div>
</template>

<style scoped>
.two-col {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
  gap: 16px;
}

/* 「待处理 N 条」快捷入口：不亮点时是浅色胶囊，点亮表示当前正在看待处理（不限日期） */
.pending-pill {
  border: 1px solid #f3d6d6;
  background: #fff5f5;
  color: #c0392b;
  font-size: 12.5px;
  font-weight: 600;
  padding: 6px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: 0.15s;
}

.pending-pill:hover {
  background: #fdecec;
}

.pending-pill.active {
  background: #c0392b;
  border-color: #c0392b;
  color: #fff;
}
</style>
