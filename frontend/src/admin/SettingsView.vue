<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import {
  NButton,
  NCard,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NSkeleton,
  NSwitch,
  NTimePicker,
  useMessage,
} from 'naive-ui'
import { api } from '../api/client'
import { MEAL_LABELS, MEALS } from '../utils/date'

const message = useMessage()

const loading = ref(true)
const saving = ref(false)
const values = reactive({
  canteen_name: '',
  announcement: '',
  meal_times: { breakfast: '', lunch: '', dinner: '' },
  deadline: { breakfast: 0, lunch: 0, dinner: 0 },
  open_days: 7,
  feedback_enabled: true,
  review_enabled: true,
  vote_enabled: true,
})

let snapshot = null

const MEAL_HINTS = {
  breakfast: '早餐供应时间段，展示在员工端',
  lunch: '午餐供应时间段',
  dinner: '晚餐供应时间段',
}

const deadlineHint = computed(
  () => `当天的预约会在「就餐日前一天」的该时间截止，当前设置下最早可预约 ${values.open_days} 天内的餐次`,
)

function hhmmToTimestamp(value) {
  if (!value) return null
  const [hour, minute] = value.split(':').map(Number)
  const d = new Date()
  d.setHours(hour || 0, minute || 0, 0, 0)
  return d.getTime()
}

function timestampToHhmm(timestamp) {
  if (timestamp === null || timestamp === undefined) return ''
  const d = new Date(timestamp)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function fill(data) {
  values.canteen_name = data.canteen_name || ''
  values.announcement = data.announcement || ''
  values.meal_times = { ...data.meal_times }
  values.open_days = data.open_days ?? 7
  values.feedback_enabled = !!data.feedback_enabled
  values.review_enabled = !!data.review_enabled
  values.vote_enabled = !!data.vote_enabled
  MEALS.forEach((meal) => {
    values.deadline[meal] = hhmmToTimestamp(data.deadline?.[meal] || '20:00')
  })
  snapshot = JSON.parse(JSON.stringify({ ...values, deadline: rawDeadline() }))
}

function rawDeadline() {
  const result = {}
  MEALS.forEach((meal) => {
    result[meal] = timestampToHhmm(values.deadline[meal])
  })
  return result
}

async function loadSettings() {
  loading.value = true
  try {
    const data = await api.get('/settings', undefined, 'admin')
    fill(data)
  } catch (error) {
    message.error(error.message)
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!values.canteen_name.trim()) {
    message.warning('食堂名称不能为空')
    return
  }
  const payload = {
    canteen_name: values.canteen_name.trim(),
    announcement: values.announcement.trim(),
    meal_times: { ...values.meal_times },
    deadline: rawDeadline(),
    open_days: values.open_days,
    feedback_enabled: values.feedback_enabled,
    review_enabled: values.review_enabled,
    vote_enabled: values.vote_enabled,
  }
  saving.value = true
  try {
    const data = await api.put('/settings', { values: payload }, 'admin')
    fill(data)
    message.success('设置已保存')
  } catch (error) {
    message.error(error.message)
  } finally {
    saving.value = false
  }
}

function restore() {
  if (snapshot) fill({ ...snapshot, deadline: snapshot.deadline })
  message.info('已还原为上次保存的设置')
}

onMounted(loadSettings)
</script>

<template>
  <div class="admin-page">
    <div class="page-head">
      <div>
        <h2>系统设置</h2>
        <p>食堂信息、就餐时间、预约规则与功能开关</p>
      </div>
      <div class="page-actions">
        <n-button size="small" @click="restore">还原</n-button>
        <n-button size="small" type="primary" :loading="saving" @click="save">保存设置</n-button>
      </div>
    </div>

    <n-skeleton v-if="loading" text :repeat="10" />
    <template v-else>
      <n-card :bordered="false">
        <template #header>
          <div class="panel-title"><i />食堂信息</div>
        </template>
        <n-form label-placement="top" size="small">
          <n-form-item label="食堂名称">
            <n-input v-model:value="values.canteen_name" placeholder="例如 博涯小食堂" style="max-width: 320px" />
          </n-form-item>
          <n-form-item label="首页公告">
            <n-input
              v-model:value="values.announcement"
              type="textarea"
              :rows="3"
              placeholder="展示在员工端首页顶部，可留空"
              style="max-width: 620px"
            />
          </n-form-item>
        </n-form>
      </n-card>

      <n-card :bordered="false">
        <template #header>
          <div class="panel-title"><i />就餐时间</div>
        </template>
        <div class="meal-grid">
          <div v-for="meal in MEALS" :key="meal" class="meal-box">
            <div class="meal-title">{{ MEAL_LABELS[meal] }}</div>
            <n-input
              v-model:value="values.meal_times[meal]"
              size="small"
              placeholder="07:30 - 08:30"
            />
            <div class="muted tiny" style="margin-top: 6px">{{ MEAL_HINTS[meal] }}</div>
          </div>
        </div>
      </n-card>

      <n-card :bordered="false">
        <template #header>
          <div class="panel-title"><i />预约规则</div>
        </template>
        <n-form label-placement="left" label-width="120" size="small">
          <n-form-item v-for="meal in MEALS" :key="meal" :label="`${MEAL_LABELS[meal]}截止时间`">
            <n-time-picker
              :value="values.deadline[meal]"
              format="HH:mm"
              :minute-step="15"
              style="width: 160px"
              @update:value="values.deadline[meal] = $event"
            />
          </n-form-item>
          <n-form-item label="可预约天数">
            <n-input-number v-model:value="values.open_days" :min="1" :max="30" style="width: 160px" />
            <span class="muted tiny" style="margin-left: 10px">员工最多可以提前多少天预约</span>
          </n-form-item>
        </n-form>
        <div class="muted tiny">{{ deadlineHint }}</div>
      </n-card>

      <n-card :bordered="false">
        <template #header>
          <div class="panel-title"><i />功能开关</div>
        </template>
        <div class="switch-row">
          <div>
            <div class="cell-strong">意见反馈</div>
            <div class="cell-sub">关闭后员工端不显示反馈入口</div>
          </div>
          <n-switch v-model:value="values.feedback_enabled" />
        </div>
        <div class="switch-row">
          <div>
            <div class="cell-strong">菜品评价</div>
            <div class="cell-sub">关闭后员工端不能提交评价</div>
          </div>
          <n-switch v-model:value="values.review_enabled" />
        </div>
        <div class="switch-row">
          <div>
            <div class="cell-strong">最爱菜投票</div>
            <div class="cell-sub">关闭后本周投票窗口关闭</div>
          </div>
          <n-switch v-model:value="values.vote_enabled" />
        </div>
      </n-card>

      <div class="sticky-actions">
        <span class="muted tiny">修改后记得点击保存</span>
        <span style="flex: 1" />
        <n-button size="small" @click="restore">还原</n-button>
        <n-button size="small" type="primary" :loading="saving" @click="save">保存设置</n-button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.meal-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 14px;
}

.meal-box {
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid #eef1f6;
  background: #fbfcff;
}

.meal-title {
  font-size: 13px;
  font-weight: 600;
  color: #33404f;
  margin-bottom: 8px;
}

.switch-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px dashed #eef1f6;
}

.switch-row:last-child {
  border-bottom: none;
}

.sticky-actions {
  position: sticky;
  bottom: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid #eef1f6;
  box-shadow: 0 6px 18px rgba(16, 24, 40, 0.06);
  backdrop-filter: blur(6px);
}
</style>
