<script setup>
// 管理端统一的日期区间切换：今日 / 本周 / 最近30天 + 自定义日期范围。
//
// 自定义区间用「按钮 + NPopover」实现：面板里是两个普通日期选择器（开始 / 结束），
// 选完点「应用」才生效。这样不依赖透明遮挡、也不受输入法/移动端点击影响，
// 桌面和手机都能正常操作。
import { computed, ref, watch } from 'vue'
import { NButton, NDatePicker, NPopover } from 'naive-ui'

import { RANGE_KEYS, RANGE_LABELS, isoFrom, parseISO, rangeOf } from '../utils/date'

const props = defineProps({
  modelValue: { type: String, default: 'week' },
  /** 允许个别页面只给部分选项 */
  options: { type: Array, default: () => RANGE_KEYS },
  size: { type: String, default: 'small' },
})

const emit = defineEmits(['update:modelValue', 'change'])

/** 当前生效区间（可能是快捷键，也可能是自定义） */
const custom = ref(null)
const open = ref(false)
const startTs = ref(null)
const endTs = ref(null)
const tip = ref('')

const keys = computed(() => props.options)
const active = computed(() => (custom.value ? 'custom' : props.modelValue))

const display = computed(() => {
  if (custom.value) return `${custom.value.start} ~ ${custom.value.end}`
  const span = rangeOf(props.modelValue === 'custom' ? 'week' : props.modelValue)
  return `${span.start} ~ ${span.end}`
})

function emitRange(key, span) {
  emit('update:modelValue', key)
  emit('change', { key, ...span })
}

function pick(key) {
  open.value = false
  if (custom.value || key !== props.modelValue) {
    custom.value = null
    emitRange(key, rangeOf(key))
    return
  }
  // 重复点同一个快捷键也刷新一次
  emitRange(key, rangeOf(key))
}

/** 打开自定义面板：把当前区间填进去，方便微调 */
function toggleCustom() {
  if (!open.value) {
    const span = custom.value || rangeOf(props.modelValue === 'custom' ? 'week' : props.modelValue)
    startTs.value = parseISO(span.start).getTime()
    endTs.value = parseISO(span.end).getTime()
    tip.value = ''
  }
  open.value = !open.value
}

function applyCustom() {
  if (!startTs.value || !endTs.value) {
    tip.value = '请把开始和结束日期都选上'
    return
  }
  let start = isoFrom(startTs.value)
  let end = isoFrom(endTs.value)
  // 选反了就自动纠正，不让用户卡住
  if (start > end) {
    ;[start, end] = [end, start]
  }
  custom.value = { start, end }
  tip.value = ''
  open.value = false
  emitRange('custom', { start, end })
}

watch(
  () => props.modelValue,
  (key) => {
    // 父组件把 modelValue 重置为快捷键时清掉自定义态
    if (key !== 'custom' && custom.value) {
      custom.value = null
      open.value = false
    }
  },
)
</script>

<template>
  <div class="range-switch" :class="size">
    <button
      v-for="key in keys"
      :key="key"
      type="button"
      class="range-btn"
      :class="{ active: key === active }"
      @click="pick(key)"
    >
      {{ RANGE_LABELS[key] }}
    </button>

    <!-- 自定义区间：manual 触发，避免面板内的日期选择器一打开就被判成「点击外部」 -->
    <n-popover
      :show="open"
      trigger="manual"
      placement="bottom-end"
      :width="276"
      :show-arrow="false"
      class="range-popover"
    >
      <template #trigger>
        <button
          type="button"
          class="range-btn custom-btn"
          :class="{ active: active === 'custom' }"
          :title="display"
          @click="toggleCustom"
        >
          <span class="custom-text">{{ active === 'custom' ? display : '自定义' }}</span>
          <svg viewBox="0 0 16 16" width="12" height="12" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round">
            <rect x="2.5" y="3.5" width="11" height="10" rx="2" />
            <path d="M2.5 6.5h11M5.5 2v3M10.5 2v3" />
          </svg>
        </button>
      </template>

      <div class="custom-panel" @click.stop>
        <p class="cp-title">自定义日期区间</p>

        <label class="cp-row">
          <span>开始</span>
          <n-date-picker v-model:value="startTs" type="date" size="small" class="cp-input" clearable />
        </label>
        <label class="cp-row">
          <span>结束</span>
          <n-date-picker v-model:value="endTs" type="date" size="small" class="cp-input" clearable />
        </label>

        <p v-if="tip" class="cp-tip">{{ tip }}</p>

        <div class="cp-actions">
          <n-button size="tiny" @click="open = false">取消</n-button>
          <n-button size="tiny" type="primary" @click="applyCustom">应用</n-button>
        </div>
      </div>
    </n-popover>
  </div>
</template>

<style scoped>
.range-switch {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 2px;
  background: #f4f5f7;
  border-radius: 8px;
}

.range-btn {
  border: none;
  background: transparent;
  color: #6b7280;
  font-size: 12.5px;
  line-height: 1;
  padding: 7px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s, color 0.15s, box-shadow 0.15s;
  white-space: nowrap;
}

.range-btn:hover {
  color: #111827;
}

.range-btn.active {
  background: #fff;
  color: #111827;
  font-weight: 600;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
}

.range-switch.small .range-btn {
  padding: 6px 10px;
  font-size: 12px;
}

.custom-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 66px;
  justify-content: center;
}

.custom-text {
  max-width: 190px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 自定义面板 */
.custom-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.cp-title {
  margin: 0;
  font-size: 12.5px;
  font-weight: 600;
  color: #111827;
}

.cp-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12.5px;
  color: #6b7280;
}

.cp-row > span {
  flex: none;
  width: 28px;
}

.cp-input {
  flex: 1;
  min-width: 0;
}

.cp-tip {
  margin: 0;
  font-size: 12px;
  color: #c0392b;
}

.cp-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 2px;
}
</style>
