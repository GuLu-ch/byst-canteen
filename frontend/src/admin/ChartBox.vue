<template>
  <div ref="elRef" class="chart-box" :style="height === '100%' ? {} : { height }" />
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

import * as echarts from 'echarts'

const props = defineProps({
  option: { type: Object, default: () => ({}) },
  // 传 '100%' 时高度跟随父容器（配合 flex 布局撑满卡片）
  height: { type: String, default: '260px' },
})

const elRef = ref(null)
let chart = null
let observer = null

function render() {
  if (!chart) return
  chart.setOption(props.option || {}, true)
}

onMounted(() => {
  chart = echarts.init(elRef.value)
  render()
  observer = new ResizeObserver(() => chart?.resize())
  observer.observe(elRef.value)
})

watch(
  () => props.option,
  () => render(),
  { deep: true },
)

onBeforeUnmount(() => {
  observer?.disconnect()
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.chart-box {
  width: 100%;
  min-height: 0;
}
</style>
