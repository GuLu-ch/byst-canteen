import { ref } from 'vue'

import { api } from '../api/client'

/** 侧边导航小红点：待处理意见反馈数量（归档后实时归零，无需手动刷新） */
export const pendingFeedback = ref(0)

export async function refreshPendingFeedback() {
  try {
    const data = await api.get('/feedback/pending', undefined, 'admin')
    pendingFeedback.value = data?.pending || 0
  } catch {
    /* 未登录或接口异常时保持上一次的值 */
  }
}

/** 归档一条反馈后：本地先减一（小红点立刻消失），再向服务端核对 */
export function notifyFeedbackHandled() {
  pendingFeedback.value = Math.max(0, pendingFeedback.value - 1)
  refreshPendingFeedback()
}
