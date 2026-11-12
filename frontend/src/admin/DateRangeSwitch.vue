<script setup>
// 管理端统一的日期区间切换：今日 / 本周 / 最近30天 + 自定义日期范围。
// 自定义区间用 NDatePicker（popover 模式）实现：
//   组件本身渲染成一个透明的输入触发器（原生输入视觉上隐藏、点击区域铺满），
//   上面覆盖「自定义」按钮 —— 点按钮即打开日历面板，选择后回调
//   change({ key:'custom', start, end })，面板自动关闭。
import { computed, ref, watch } from 'vue'
import { NDatePicker } from 'naive-ui'

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
const pickerValue = ref(null)
const pickerVisible = ref(false)

const keys = computed(() => props.options)
const active = computed(() => (custom.value ? 'custom' : props.modelValue))

function emitRange(key, span) {
  emit('update:modelValue', key)
  emit('change', { key, ...span })
}

function pick(key) {
  if (custom.value || key !== props.modelValue) {
    custom.value = null
    pickerValue.value = null
    emitRange(key, rangeOf(key))
    return
  }
  // 重复点同一个快捷键也刷新一次
  emitRange(key, rangeOf(key))
}

function openPicker() {
  // 面板打开时预填当前区间，方便微调
  const span = custom.value || rangeOf(props.modelValue === 'custom' ? 'week' : props.modelValue)
  pickerValue.value = [parseISO(span.start).getTime(), parseISO(span.end).getTime()]
}

function pickerChanged(value) {
  if (!value || value.length !== 2) return
  // daterange 无确认按钮（actions=null）：点完第二下即提交
  const start = isoFrom(value[0])
  const end = isoFrom(value[1])
  custom.value = { start, end }
  emitRange('custom', { start, end })
}

const display = computed(() => {
  if (custom.value) return `${custom.value.start} ~ ${custom.value.end}`
  const span = rangeOf(props.modelValue === 'custom' ? 'week' : props.modelValue)
  return `${span.start} ~ ${span.end}`
})

watch(
  () => props.modelValue,
  (key) => {
    // 父组件把 modelValue 重置为快捷键时清掉自定义态
    if (key !== 'custom' && custom.value) {
      custom.value = null
      pickerValue.value = null
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

    <!--
      自定义区间：NDatePicker（popover 模式）透明地铺在「自定义」按钮下面，
      原生输入隐藏、点击落在日历触发器上；面板打开时预填当前区间。
    -->
    <div class="custom-wrap">
      <button type="button" class="range-btn custom-btn" :class="{ active: active === 'custom' }" :title="display" tabindex="-1">
        <span class="custom-text">{{ active === 'custom' ? display : '自定义' }}</span>
        <svg viewBox="0 0 16 16" width="12" height="12" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round">
          <rect x="2.5" y="3.5" width="11" height="10" rx="2" />
          <path d="M2.5 6.5h11M5.5 2v3M10.5 2v3" />
        </svg>
      </button>
      <n-date-picker
        :value="pickerValue"
        type="daterange"
        size="small"
        :actions="null"
        :clearable="false"
        class="picker-ghost"
        @update:show="(show) => (show ? openPicker() : null)"
        @update:value="pickerChanged"
      />
    </div>
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

/* 自定义按钮 + 透明日期选择器叠放：按钮负责显示，选择器负责接收点击 */
.custom-wrap {
  position: relative;
  display: inline-flex;
  margin-left: 2px;
}

.custom-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 66px;
  justify-content: center;
}

.picker-ghost {
  position: absolute;
  inset: 0;
  width: 100%;
  opacity: 0;
  cursor: pointer;
}

.picker-ghost :deep(.n-input) {
  height: 100%;
  min-height: 0;
  background: transparent;
  border: none;
  box-shadow: none;
  --n-padding-single: 0;
  --n-padding-start: 0;
  --n-padding-end: 0;
}

.custom-text {
  max-width: 190px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
