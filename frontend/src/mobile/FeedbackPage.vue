<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import AppIcon from '../components/AppIcon.vue'
import { api } from '../api/client'
import { formatDateTime } from '../utils/date'

const router = useRouter()

const categories = [
  { key: 'taste', label: '口味咸淡', icon: '🧂' },
  { key: 'oil', label: '菜品太油', icon: '🫗' },
  { key: 'fresh', label: '食材新鲜度', icon: '🥬' },
  { key: 'hygiene', label: '卫生问题', icon: '🧼' },
  { key: 'tableware', label: '餐具问题', icon: '🥢' },
  { key: 'other', label: '其他建议', icon: '💡' },
]

const category = ref('taste')
const content = ref('')
const submitting = ref(false)
const mine = ref([])

const labelOf = (key) => categories.find((item) => item.key === key)?.label || key

async function loadMine() {
  mine.value = (await api.get('/feedback/mine', { limit: 20 })) || []
}

async function submit() {
  if (content.value.trim().length < 4) {
    showToast('再多写几个字吧')
    return
  }
  submitting.value = true
  try {
    await api.post('/feedback', { category: category.value, content: content.value.trim() })
    showToast('感谢反馈，已匿名提交')
    content.value = ''
    await loadMine()
  } catch (error) {
    showToast(error.message || '提交失败')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadMine().catch(() => {})
})
</script>

<template>
  <div class="fb-page">
    <header class="head">
      <button type="button" class="back" @click="router.back()">
        <AppIcon name="chevron-left" :size="18" />
      </button>
      <h1>意见反馈</h1>
      <span class="pill"><AppIcon name="shield" :size="12" /> 完全匿名</span>
    </header>

    <div class="page">
      <div class="card intro">
        <p class="intro-title">说说今天的饭菜吧</p>
        <p class="intro-text">
          口味咸淡、菜品是否太油、食材是否新鲜、卫生与餐具问题都可以提。反馈全程匿名，厨师和管理员只能看到内容。
        </p>
      </div>

      <div class="card">
        <p class="label">反馈类型</p>
        <div class="cats">
          <button
            v-for="item in categories"
            :key="item.key"
            type="button"
            class="cat"
            :class="{ active: category === item.key }"
            @click="category = item.key"
          >
            <span class="cat-icon">{{ item.icon }}</span>
            {{ item.label }}
          </button>
        </div>

        <p class="label second">具体内容</p>
        <van-field
          v-model="content"
          type="textarea"
          rows="4"
          maxlength="300"
          show-word-limit
          placeholder="例如：今天的青菜偏咸，油也有点多，希望清淡一些～"
          class="textarea"
        />

        <button type="button" class="primary-btn full" :disabled="submitting" @click="submit">
          {{ submitting ? '提交中…' : '匿名提交' }}
        </button>
        <p class="hint">提交后厨师和食堂管理员会尽快看到，不会显示你的姓名和手机号。</p>
      </div>

      <section class="card list">
        <div class="section-head">
          <h3>我的反馈</h3>
          <span class="muted small">{{ mine.length }} 条</span>
        </div>
        <div v-if="!mine.length" class="empty">
          <AppIcon name="message" :size="26" />
          <span>还没有提交过反馈</span>
        </div>
        <div v-for="item in mine" :key="item.id" class="item">
          <div class="item-top">
            <span class="pill">{{ item.category_label || labelOf(item.category) }}</span>
            <span class="muted small">{{ formatDateTime(item.created_at) }}</span>
            <span class="spacer" />
            <span class="status" :class="{ done: item.handled }">{{ item.handled ? '已处理' : '待处理' }}</span>
          </div>
          <p class="item-content">{{ item.content }}</p>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
/* 底部导航之上留出余量 */
.fb-page {
  padding-bottom: calc(70px + env(safe-area-inset-bottom));
}

.head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 16px 4px;
}

.head h1 {
  flex: 1;
  font-size: 18px;
  font-weight: 700;
  color: var(--text);
}

.back {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border: 1px solid var(--line);
  border-radius: 11px;
  background: var(--card);
  color: var(--text-2);
}

.small {
  font-size: 12px;
}

.card {
  padding: 14px;
  margin-bottom: 12px;
}

.intro {
  background: var(--brand-softer);
  border: 1px solid var(--brand-soft);
}

.intro-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
}

.intro-text {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.65;
  color: var(--text-2);
}

.label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-2);
}

.label.second {
  margin-top: 16px;
}

.cats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-top: 8px;
}

.cat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  padding: 10px 4px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--card-2);
  color: var(--text-2);
  font-size: 12px;
  font-family: inherit;
  transition: all 0.18s ease;
}

.cat-icon {
  font-size: 18px;
}

.cat.active {
  border-color: transparent;
  background: var(--brand-soft);
  box-shadow: inset 0 0 0 1.5px var(--brand);
  color: var(--brand-dark);
  font-weight: 600;
}

html[data-theme='dark'] .cat.active {
  color: #7cd8fb;
}

.textarea {
  margin-top: 8px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--card-2);
  overflow: hidden;
}

.full {
  width: 100%;
  margin-top: 14px;
}

.hint {
  margin-top: 10px;
  font-size: 11px;
  color: var(--text-3);
  line-height: 1.6;
}

.list {
  margin-top: 4px;
}

.item {
  padding: 11px 0;
  border-bottom: 1px solid var(--line);
}

.item:last-child {
  border-bottom: none;
}

.item-top {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status {
  font-size: 11px;
  color: var(--amber);
  font-weight: 600;
}

.status.done {
  color: var(--green);
}

.item-content {
  margin-top: 6px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-2);
}
</style>
