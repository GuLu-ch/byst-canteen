<script setup>
// 管理端独立登录页：账号 + 密码（不是手机号），凭证由后端写入 httpOnly cookie。
// 与用户端（员工手机号登录）完全分离，两端页面互不提供切换入口。
// 注意：本页不在管理端 Layout 内，没有 n-message-provider，
// 所以不能用 useMessage()（会直接抛错导致白屏），错误提示走页面内横幅。
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NCheckbox, NConfigProvider, NForm, NFormItem, NInput, dateZhCN, zhCN } from 'naive-ui'

import { themeOverrides } from '../admin/naive'
import { adminLogin } from '../stores/app'

const router = useRouter()
const route = useRoute()

const formRef = ref(null)
const model = ref({ account: localStorage.getItem('byst_admin_account') || '', password: '' })
const remember = ref(!!localStorage.getItem('byst_admin_account'))
const loading = ref(false)
const errorText = ref('')

const rules = {
  account: { required: true, message: '请输入账号', trigger: 'blur' },
  password: { required: true, message: '请输入密码', trigger: 'blur' },
}

async function submit(event) {
  event?.preventDefault?.()
  errorText.value = ''
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  loading.value = true
  try {
    await adminLogin(model.value.account.trim(), model.value.password)
    if (remember.value) localStorage.setItem('byst_admin_account', model.value.account.trim())
    else localStorage.removeItem('byst_admin_account')
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : ''
    router.replace(redirect.startsWith('/admin') ? redirect : '/admin')
  } catch (error) {
    errorText.value = error.message || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <n-config-provider :theme-overrides="themeOverrides" :locale="zhCN" :date-locale="dateZhCN">
    <div class="admin-login">
      <div class="panel">
        <aside class="brand">
          <div class="brand-top">
            <span class="logo-mark">
              <svg viewBox="0 0 48 48" width="26" height="26" fill="none" stroke="#fff" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round">
                <path d="M8 22h32c0 9.4-7.2 16-16 16S8 31.4 8 22Z" />
                <path d="M18 15c0-2.5 2-3.5 2-5.5M26 15c0-2.5 2-3.5 2-5.5" />
              </svg>
            </span>
            <div class="brand-name">
              <strong>博涯小食堂</strong>
              <i>Management Console</i>
            </div>
          </div>

          <div class="brand-copy">
            <h2>管理后台</h2>
            <p>菜单排期、就餐统计、意见反馈，一处打理。</p>
          </div>

          <ul class="brand-list">
            <li><span></span>管理员 / 厨师专用入口</li>
            <li><span></span>员工请使用手机号在用户端登录</li>
            <li><span></span>两端账号与登录态互不影响</li>
          </ul>
        </aside>

        <section class="form-side">
          <header class="form-head">
            <h1>登录</h1>
            <p>请输入管理端账号与密码</p>
          </header>

          <p v-if="errorText" class="error-banner">{{ errorText }}</p>

          <n-form
            ref="formRef"
            :model="model"
            :rules="rules"
            size="large"
            label-placement="top"
            :show-require-mark="false"
            @keyup.enter="submit"
          >
            <n-form-item label="账号" path="account">
              <n-input
                v-model:value="model.account"
                placeholder="管理员账号"
                :input-props="{ autocomplete: 'username' }"
              />
            </n-form-item>
            <n-form-item label="密码" path="password">
              <n-input
                v-model:value="model.password"
                type="password"
                show-password-on="click"
                placeholder="登录密码"
                :input-props="{ autocomplete: 'current-password' }"
              />
            </n-form-item>

            <div class="row-between">
              <n-checkbox v-model:checked="remember">记住账号</n-checkbox>
              <span class="hint">忘记密码请联系系统管理员</span>
            </div>

            <n-button type="primary" block size="large" :loading="loading" class="submit" @click="submit">
              进入后台
            </n-button>
          </n-form>

          <p class="foot">博涯科技 · 食堂管理端</p>
        </section>
      </div>
    </div>
  </n-config-provider>
</template>

<style scoped>
.admin-login {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 28px;
  background: #f6f7f9;
  color: #111827;
}

.panel {
  width: 860px;
  max-width: 100%;
  display: grid;
  grid-template-columns: 1fr 1fr;
  background: #fff;
  border: 1px solid #edeff3;
  border-radius: 18px;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.07);
  overflow: hidden;
}

.brand {
  padding: 38px 34px;
  background: linear-gradient(160deg, #f8fafc, #f1f5f9);
  border-right: 1px solid #eef1f5;
  display: flex;
  flex-direction: column;
  gap: 34px;
}

.brand-top {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-mark {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: #111827;
  display: grid;
  place-items: center;
  flex: none;
}

.brand-name {
  display: flex;
  flex-direction: column;
  line-height: 1.3;
}

.brand-name strong {
  font-size: 15px;
  letter-spacing: 0.4px;
  color: #111827;
}

.brand-name i {
  font-style: normal;
  font-size: 10.5px;
  letter-spacing: 1.3px;
  text-transform: uppercase;
  color: #9aa3af;
}

.brand-copy h2 {
  margin: 0;
  font-size: 26px;
  letter-spacing: 0.5px;
  color: #0f172a;
}

.brand-copy p {
  margin: 10px 0 0;
  font-size: 13px;
  line-height: 1.8;
  color: #6b7280;
}

.brand-list {
  margin: auto 0 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.brand-list li {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 12.5px;
  color: #6b7280;
}

.brand-list span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #cbd5e1;
  flex: none;
}

.form-side {
  padding: 40px 40px 26px;
  display: flex;
  flex-direction: column;
}

.form-head h1 {
  margin: 0;
  font-size: 22px;
  color: #0f172a;
  letter-spacing: 0.5px;
}

.form-head p {
  margin: 7px 0 22px;
  font-size: 12.5px;
  color: #8b95a3;
}

.error-banner {
  margin: 0 0 16px;
  padding: 9px 12px;
  border-radius: 8px;
  background: #fef2f2;
  border: 1px solid #fbdcdc;
  color: #b42318;
  font-size: 12.5px;
  line-height: 1.6;
}

.row-between {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 2px 0 20px;
  gap: 10px;
}

.hint {
  font-size: 12px;
  color: #a8b1bd;
}

.submit {
  height: 44px;
  font-weight: 600;
}

.foot {
  margin: 22px 0 0;
  text-align: center;
  font-size: 11.5px;
  color: #a8b1bd;
}

@media (max-width: 760px) {
  .panel {
    grid-template-columns: 1fr;
  }

  .brand {
    padding: 26px 24px;
    gap: 18px;
    border-right: none;
    border-bottom: 1px solid #eef1f5;
  }

  .brand-copy h2 {
    font-size: 20px;
  }

  .brand-list {
    display: none;
  }

  .form-side {
    padding: 26px 24px 20px;
  }
}
</style>
