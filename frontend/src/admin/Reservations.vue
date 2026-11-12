<script setup>
import { computed, h, onMounted, ref } from 'vue'
import {
  NButton,
  NCard,
  NDataTable,
  NDrawer,
  NDrawerContent,
  NIcon,
  NSkeleton,
  NTag,
  useMessage,
} from 'naive-ui'
import { DownloadOutline } from '@vicons/ionicons5'
import DateRangeSwitch from './DateRangeSwitch.vue'
import { useIsMobile } from './useIsMobile'
import { api, downloadBlob } from '../api/client'
import { MEAL_LABELS, MEALS, addDays, rangeOf, todayISO } from '../utils/date'

const message = useMessage()
const isMobile = useIsMobile()

const rangeKey = ref('week')
/** 自定义区间（选择「自定义」时使用） */
const customRange = ref(null)
const loading = ref(true)
const summary = ref({ days: [], total: 0 })

const detailVisible = ref(false)
const detailLoading = ref(false)
const detail = ref({ date: '', meal: 'lunch', total: 0, items: [], departments: [] })
const detailMeal = ref('lunch')

const range = computed(() => customRange.value || rangeOf(rangeKey.value === 'custom' ? 'week' : rangeKey.value))
const rangeStart = computed(() => range.value.start)
const rangeEnd = computed(() => range.value.end)
const rangeText = computed(() => `${rangeStart.value} ~ ${rangeEnd.value}`)

const WEEKDAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

const stats = computed(() => {
  const days = summary.value.days || []
  const today = days.find((day) => day.date === todayISO())
  const tomorrow = days.find((day) => day.date === addDays(todayISO(), 1))
  const activeDays = days.filter((day) => day.weekday < 5).length || 1
  return [
    { label: '区间总人次', value: summary.value.total || 0, unit: '人次', foot: rangeText.value },
    { label: '今日就餐', value: today?.total || 0, unit: '人', foot: `早 ${today?.meals.breakfast || 0} · 午 ${today?.meals.lunch || 0} · 晚 ${today?.meals.dinner || 0}` },
    { label: '明日就餐', value: tomorrow?.total || 0, unit: '人', foot: `早 ${tomorrow?.meals.breakfast || 0} · 午 ${tomorrow?.meals.lunch || 0} · 晚 ${tomorrow?.meals.dinner || 0}` },
    { label: '工作日日均', value: Math.round((summary.value.total || 0) / activeDays), unit: '人次', foot: `按 ${activeDays} 个工作日折算` },
  ]
})

const columns = [
  {
    title: '日期',
    key: 'date',
    width: 190,
    render: (row) =>
      h('div', null, [
        h('div', { class: 'cell-strong' }, row.date),
        h('div', { class: 'cell-sub' }, WEEKDAYS[row.weekday]),
      ]),
  },
  ...MEALS.map((meal) => ({
    title: MEAL_LABELS[meal],
    key: meal,
    align: 'center',
    render: (row) => row.meals[meal] || 0,
  })),
  {
    title: '当日合计',
    key: 'total',
    align: 'center',
    render: (row) =>
      h(
        NTag,
        { type: row.total > 0 ? 'info' : 'default', bordered: false, round: true },
        { default: () => `${row.total} 人` },
      ),
  },
  {
    title: '操作',
    key: 'actions',
    align: 'center',
    width: 160,
    render: (row) =>
      h(
        NButton,
        { size: 'small', quaternary: true, type: 'primary', onClick: () => openDetail(row.date) },
        { default: () => '查看明细' },
      ),
  },
]

const detailColumns = [
  {
    title: '姓名',
    key: 'name',
    render: (row) =>
      h('div', null, [
        h('div', { class: 'cell-strong' }, row.name),
        h('div', { class: 'cell-sub' }, row.phone),
      ]),
  },
  { title: '部门', key: 'department', render: (row) => row.department || '—' },
  {
    title: '忌口 / 偏好',
    key: 'prefs',
    render: (row) =>
      h('div', { style: 'display:flex;gap:6px;flex-wrap:wrap' }, [
        row.allergens ? h('span', { class: 'chip bad' }, `忌口：${row.allergens}`) : null,
        row.preferences ? h('span', { class: 'chip' }, row.preferences) : null,
      ]),
  },
]

async function load() {
  loading.value = true
  try {
    summary.value = await api.get('/reservations/summary', { start: rangeStart.value, end: rangeEnd.value }, 'admin')
  } catch (error) {
    message.error(error.message)
  } finally {
    loading.value = false
  }
}

async function openDetail(day) {
  detailVisible.value = true
  detailMeal.value = 'lunch'
  await loadDetail(day, 'lunch')
}

async function loadDetail(day, meal) {
  detailLoading.value = true
  detailMeal.value = meal
  try {
    detail.value = await api.get('/reservations/detail', { day, meal }, 'admin')
  } catch (error) {
    message.error(error.message)
  } finally {
    detailLoading.value = false
  }
}

async function exportExcel() {
  try {
    const blob = await api.blob('/reservations/export', { start: rangeStart.value, end: rangeEnd.value }, 'admin')
    downloadBlob(blob, `就餐预约_${rangeStart.value}_${rangeEnd.value}.xlsx`)
    message.success('已导出 Excel')
  } catch (error) {
    message.error(error.message)
  }
}

function onRangeChange({ key, start, end }) {
  rangeKey.value = key
  customRange.value = key === 'custom' ? { start, end } : null
  load()
}

onMounted(load)
</script>

<template>
  <div class="admin-page">
    <div class="page-head">
      <div>
        <h2>就餐预约</h2>
        <p>按日期查看早中晚三餐的就餐人数，可导出 Excel 交给后厨备餐</p>
      </div>
      <div class="page-actions">
        <DateRangeSwitch v-model="rangeKey" @change="onRangeChange" />
        <n-button type="primary" size="small" @click="exportExcel">
          <template #icon><n-icon :component="DownloadOutline" /></template>
          导出 Excel
        </n-button>
      </div>
    </div>

    <div class="stat-grid">
      <div v-for="item in stats" :key="item.label" class="stat">
        <div class="stat-label">{{ item.label }}</div>
        <div class="stat-value">{{ item.value }}<small>{{ item.unit }}</small></div>
        <div class="stat-foot">{{ item.foot }}</div>
      </div>
    </div>

    <n-card :bordered="false">
      <template #header>
        <div class="panel-head">
          <div class="panel-title"><i />每日就餐人数</div>
          <span class="panel-sub">周六日不供餐</span>
        </div>
      </template>
      <n-skeleton v-if="loading" text :repeat="6" />
      <n-data-table
        v-else
        :columns="columns"
        :data="summary.days"
        :bordered="false"
        :single-line="false"
        size="small"
        :row-key="(row) => row.date"
        :scroll-x="640"
      />
    </n-card>

    <n-drawer v-model:show="detailVisible" :width="isMobile ? '100%' : 640" placement="right">
      <n-drawer-content closable :native-scrollbar="false" body-content-style="padding: 14px">
        <template #header>{{ detail.date }} 就餐名单</template>
        <div class="detail-toolbar">
          <n-button
            v-for="meal in MEALS"
            :key="meal"
            size="small"
            :type="detailMeal === meal ? 'primary' : 'default'"
            :ghost="detailMeal !== meal"
            @click="loadDetail(detail.date, meal)"
          >
            {{ MEAL_LABELS[meal] }}
          </n-button>
          <span class="chip ok">共 {{ detail.total }} 人</span>
        </div>

        <div v-if="detail.departments.length" class="detail-depts">
          <span v-for="dept in detail.departments" :key="dept.name" class="chip">
            {{ dept.name }} · {{ dept.count }}
          </span>
        </div>

        <n-skeleton v-if="detailLoading" text :repeat="6" />

        <!-- 手机端：卡片列表，姓名/部门/忌口一屏看全 -->
        <div v-else-if="isMobile" class="detail-cards">
          <article v-for="row in detail.items" :key="row.phone" class="detail-card">
            <div class="dc-head">
              <strong>{{ row.name }}</strong>
              <span class="muted tiny">{{ row.department || '—' }}</span>
            </div>
            <div class="dc-phone">{{ row.phone }}</div>
            <div v-if="row.allergens || row.preferences" class="dc-tags">
              <span v-if="row.allergens" class="chip bad">忌口：{{ row.allergens }}</span>
              <span v-if="row.preferences" class="chip">{{ row.preferences }}</span>
            </div>
          </article>
          <div v-if="!detail.items.length" class="empty-box">这一餐还没有人预约</div>
        </div>

        <template v-else>
          <n-data-table
            :columns="detailColumns"
            :data="detail.items"
            :bordered="false"
            size="small"
            max-height="60vh"
          />
          <div v-if="!detail.items.length" class="empty-box">这一餐还没有人预约</div>
        </template>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<style scoped>
.detail-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.detail-depts {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.detail-cards {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.detail-card {
  border: 1px solid #eceef2;
  border-radius: 10px;
  padding: 10px 12px;
  background: #fff;
}

.dc-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
}

.dc-head strong {
  font-size: 14px;
  color: #111827;
}

.dc-phone {
  margin-top: 2px;
  font-size: 12px;
  color: #9aa3af;
}

.dc-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}
</style>
