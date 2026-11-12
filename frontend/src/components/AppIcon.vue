<script setup>
import { computed } from 'vue'

/**
 * 轻量 SVG 图标集（24×24，线性描边，颜色跟随 currentColor）。
 * 全部手绘路径，避免额外引入图标库、移动端首屏更小。
 */
const ICONS = {
  home: ['M3.2 10.6 12 3.4l8.8 7.2', 'M5.6 9.4V20.2h4.3v-5.3h4.2v5.3h4.3V9.4'],
  menu: ['M3.6 11.2h16.8a8.4 8.4 0 0 1-16.8 0Z', 'M9 7.4c0-1.2 1.2-1.6 1.2-2.9M13.8 7.4c0-1.2 1.2-1.6 1.2-2.9', 'M3.4 20.6h17.2'],
  star: ['M12 3.6l2.72 5.5 6.08.89-4.4 4.29 1.04 6.06L12 17.5l-5.44 2.84 1.04-6.06-4.4-4.29 6.08-.89Z'],
  user: ['M12 12.2a4.1 4.1 0 1 0 0-8.2 4.1 4.1 0 0 0 0 8.2Z', 'M4.4 20.8a7.6 7.6 0 0 1 15.2 0'],
  calendar: ['M4 7.6h16v12.6H4z', 'M8.2 3.6v4M15.8 3.6v4M4 11.8h16'],
  clock: ['M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z', 'M12 7.6V12l3 1.9'],
  bell: ['M18.2 16.6H5.8L7.4 14.3V9.9a4.6 4.6 0 0 1 9.2 0v4.4Z', 'M9.9 19.4a2.1 2.1 0 0 0 4.2 0'],
  check: ['M5 12.6l4.6 4.6L19.2 6.8'],
  'check-circle': ['M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z', 'M8 12.3l2.8 2.8L16.2 9.6'],
  close: ['M6.4 6.4l11.2 11.2M17.6 6.4L6.4 17.6'],
  plus: ['M12 5.2v13.6M5.2 12h13.6'],
  edit: ['M4 20h4L19 9l-4-4L4 16v4Z', 'M14.2 6.2l3.6 3.6'],
  lock: ['M6.4 10.6h11.2v9.6H6.4z', 'M9 10.6V8.2a3 3 0 0 1 6 0v2.4'],
  logout: ['M9.4 4.4H6.6A1.6 1.6 0 0 0 5 6v12a1.6 1.6 0 0 0 1.6 1.6h2.8', 'M15.6 8.2 19.4 12l-3.8 3.8', 'M9.6 12h9.4'],
  message: ['M4 5.4h16v11.2H9.4L4 20.4z', 'M8 9.4h8M8 12.6h5'],
  chart: ['M4 19.4h16', 'M7.4 19.4v-6.2M12 19.4V6.6M16.6 19.4v-9'],
  shield: ['M12 3.2l7 2.8v6.2c0 4.2-3 7.4-7 8.8-4-1.4-7-4.6-7-8.8V6Z', 'M9.2 12l2 2 3.6-3.6'],
  heart: ['M12 20.2S4.6 15.5 4.6 10.6A3.9 3.9 0 0 1 12 8.4a3.9 3.9 0 0 1 7.4 2.2c0 4.9-7.4 9.6-7.4 9.6Z'],
  sparkles: ['M11.6 3.4l1.7 4.6 4.6 1.7-4.6 1.7-1.7 4.6-1.7-4.6L5.3 9.7l4.6-1.7Z', 'M18.4 14.6l.8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8Z'],
  'thumbs-up': ['M7.4 11v8.6H4.2V11z', 'M7.4 11 11.6 4a2 2 0 0 1 3.6 1.3V9h3.2a2 2 0 0 1 1.98 2.3l-1.24 6.1a2.2 2.2 0 0 1-2.16 1.8H7.4'],
  utensils: ['M8.2 3.4v6a2 2 0 0 0 4 0v-6', 'M10.2 9.4v11.2', 'M16.6 3.4c-1.4 1.6-1.9 3.1-1.9 5.4 0 1.6.8 2.4 1.9 2.4s1.9-.8 1.9-2.4c0-2.3-.5-3.8-1.9-5.4Z', 'M16.6 11.2v9.4'],
  bowl: ['M3.4 11h17.2a8.6 8.6 0 0 1-17.2 0Z', 'M3.2 20.6h17.6', 'M12 7.4c0-1.4 1.4-1.8 1.4-3.2'],
  download: ['M12 4v10.4', 'M8 11.2l4 4 4-4', 'M5 19.4h14'],
  upload: ['M12 20.2V9.8', 'M8 13.4l4-4 4 4', 'M5 4.6h14'],
  search: ['M11 18.4a7.4 7.4 0 1 0 0-14.8 7.4 7.4 0 0 0 0 14.8Z', 'M16.6 16.6 20.6 20.6'],
  copy: ['M9.4 9.4h10.2v10.2H9.4z', 'M14.6 6.6V4.4H4.4v10.2h2.2'],
  trash: ['M4.4 7.2h15.2', 'M9.4 7.2V4.4h5.2v2.8', 'M6.6 7.2l.9 12.4h9l.9-12.4'],
  info: ['M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z', 'M12 11v5.6', 'M12 8.1v.1'],
  grid: ['M4.4 4.4h6v6h-6zM13.6 4.4h6v6h-6zM4.4 13.6h6v6h-6zM13.6 13.6h6v6h-6z'],
  'chevron-left': ['M15 5.4 8.4 12 15 18.6'],
  'chevron-right': ['M9 5.4 15.6 12 9 18.6'],
  'chevron-down': ['M5.4 9 12 15.6 18.6 9'],
  refresh: ['M19.4 12a7.4 7.4 0 1 1-2.4-5.4', 'M19.6 4.6v4.2h-4.2'],
  flame: ['M12 21c3.6 0 6-2.3 6-5.4 0-3.9-4.2-5.2-4.2-8.8 0-.9.3-1.7.8-2.4-3.3.7-5.4 3.5-5.4 6.4 0 1 .2 1.6.2 2.2 0 .8-.6 1.4-1.4 1.4-.9 0-1.6-.7-1.8-1.7-.9 1.1-1.4 2.5-1.4 4 0 3 2.6 4.3 6.2 4.3Z'],
  moon: ['M20.2 13.6A8.2 8.2 0 0 1 10.4 3.8a8.2 8.2 0 1 0 9.8 9.8Z'],
  sun: ['M12 16.4a4.4 4.4 0 1 0 0-8.8 4.4 4.4 0 0 0 0 8.8Z', 'M12 2.6v2.2M12 19.2v2.2M2.6 12h2.2M19.2 12h2.2M5.4 5.4l1.5 1.5M17.1 17.1l1.5 1.5M18.6 5.4l-1.5 1.5M6.9 17.1l-1.5 1.5'],
}

const props = defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 20 },
  filled: { type: Boolean, default: false },
  strokeWidth: { type: [Number, String], default: 1.8 },
})

const paths = computed(() => ICONS[props.name] || ICONS.info)
const px = computed(() => (typeof props.size === 'number' ? `${props.size}px` : props.size))
</script>

<template>
  <svg
    class="app-icon"
    viewBox="0 0 24 24"
    :style="{ width: px, height: px }"
    :fill="filled ? 'currentColor' : 'none'"
    stroke="currentColor"
    :stroke-width="strokeWidth"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path v-for="(d, index) in paths" :key="index" :d="d" />
  </svg>
</template>

<style scoped>
.app-icon {
  flex: none;
  display: block;
}
</style>
