<template>
  <div class="login-page">
    <div class="glow glow-a"></div>
    <div class="glow glow-b"></div>

    <div class="brand">
      <div class="logo"><AppIcon name="bowl" :size="34" :stroke-width="1.9" /></div>
      <h1>{{ settings?.canteen_name || '博涯小食堂' }}</h1>
      <p class="slogan">今天也要好好吃饭</p>
    </div>

    <div class="login-card">
      <van-form @submit="submit">
        <van-cell-group inset :border="false">
          <van-field
            v-model="phone"
            name="phone"
            type="tel"
            maxlength="11"
            label="手机号"
            placeholder="请输入手机号"
            clearable
            :rules="[{ validator: (v) => /^1\d{10}$/.test(v), message: '请输入 11 位手机号' }]"
          />
          <van-field
            v-model="password"
            name="password"
            type="password"
            label="密码"
            placeholder="请输入密码"
            :rules="[{ required: true, message: '请输入密码' }]"
          />
        </van-cell-group>

        <div class="actions">
          <van-checkbox v-model="remember" icon-size="16px">记住手机号</van-checkbox>
          <span class="muted small">初始密码 123456</span>
        </div>

        <van-button block type="primary" native-type="submit" :loading="loading" round class="submit">
          登录
        </van-button>
      </van-form>

      <p class="tips">打开网页自动进入，忘记密码请联系管理员重置</p>
    </div>

    <p class="footer">博涯科技 · 员工食堂服务</p>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'

import { login, store } from '../stores/app'
import AppIcon from '../components/AppIcon.vue'

const route = useRoute()
const router = useRouter()

const phone = ref(localStorage.getItem('byst_phone') || '')
const password = ref('')
const remember = ref(!!localStorage.getItem('byst_phone'))
const loading = ref(false)
const settings = ref(store.settings)

onMounted(async () => {
  settings.value = store.settings
})

async function submit() {
  loading.value = true
  try {
    const user = await login(phone.value.trim(), password.value)
    if (remember.value) localStorage.setItem('byst_phone', phone.value.trim())
    else localStorage.removeItem('byst_phone')

    showToast(`欢迎回来，${user.name}`)
    const redirect = route.query.redirect
    if (typeof redirect === 'string' && redirect.startsWith('/') && !redirect.startsWith('/admin')) {
      router.replace(redirect)
    } else {
      router.replace({ name: 'home' })
    }
  } catch (error) {
    showToast(error.message || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  position: relative;
  min-height: 100%;
  padding: 56px 20px 32px;
  background: linear-gradient(160deg, #eefaff 0%, #f7f9fc 46%, #f1f4f8 100%);
  overflow: hidden;
}

html[data-theme='dark'] .login-page {
  background: linear-gradient(160deg, #0d1620 0%, #101c28 46%, #0d1620 100%);
}

.glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(48px);
  opacity: 0.55;
  pointer-events: none;
}

.glow-a {
  width: 220px;
  height: 220px;
  top: -70px;
  right: -60px;
  background: #b8e8fb;
}

html[data-theme='dark'] .glow-a {
  background: rgba(5, 175, 240, 0.25);
}

.glow-b {
  width: 180px;
  height: 180px;
  bottom: 40px;
  left: -70px;
  background: #d2f0fd;
}

html[data-theme='dark'] .glow-b {
  background: rgba(2, 132, 199, 0.22);
}

.brand {
  position: relative;
  text-align: center;
  margin-bottom: 28px;
}

.logo {
  width: 68px;
  height: 68px;
  margin: 0 auto 14px;
  border-radius: 22px;
  background: linear-gradient(140deg, #4ac6f5, #05aff0);
  box-shadow: 0 14px 28px rgba(5, 175, 240, 0.32);
  display: grid;
  place-items: center;
  color: #fff;
}

.brand h1 {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: 1px;
  color: var(--text);
}

.slogan {
  margin-top: 6px;
  font-size: 13px;
  color: var(--text-3);
}

.login-card {
  position: relative;
  background: var(--card);
  border-radius: 22px;
  padding: 18px 14px 16px;
  box-shadow: 0 18px 40px rgba(23, 31, 53, 0.08);
}

:deep(.van-cell-group--inset) {
  margin: 0;
  border-radius: 14px;
  background: var(--card-2);
}

:deep(.van-field) {
  background: transparent;
  padding: 12px 12px;
}

.actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 6px 4px;
}

.small {
  font-size: 12px;
}

.submit {
  margin-top: 10px;
  height: 46px;
  font-size: 16px;
  font-weight: 600;
  box-shadow: 0 10px 22px rgba(5, 175, 240, 0.28);
}

.tips {
  margin-top: 14px;
  text-align: center;
  font-size: 12px;
  color: var(--text-3);
}

.footer {
  position: relative;
  margin-top: 36px;
  text-align: center;
  font-size: 12px;
  color: var(--text-3);
}
</style>
