import { createApp } from 'vue'
import Vant from 'vant'
import 'vant/lib/index.css'

import App from './App.vue'
import router from './router'
import { setApp } from './app-ref'
import { setUnauthorizedHandler } from './api/client'
import { store } from './stores/app'
import './styles/base.css'

const app = createApp(App)
setApp(app)
app.use(router)
app.use(Vant)

// 401 时统一回到对应入口的登录页（用户端与管理端登录分离），并带上当前地址方便登录后跳回
setUnauthorizedHandler((kind) => {
  const current = router.currentRoute.value
  if (kind === 'admin') {
    store.admin = null
    store.adminReady = false
    if (current.name !== 'admin-login') {
      router.replace({ name: 'admin-login', query: { redirect: current.fullPath } })
    }
    return
  }
  store.user = null
  if (current.name !== 'login') {
    router.replace({ name: 'login', query: { redirect: current.fullPath } })
  }
})

app.mount('#app')
