/**
 * 保存 Vue 应用实例的极简模块。
 *
 * 为什么单独放一个文件：管理端的 Naive UI 需要在进入 /admin 之前用 app.use 安装，
 * 但 main.js 里如果直接 import admin/naive.js，整个 Naive UI 就会被塞进移动端首屏包。
 * 用这个不含任何依赖的小模块传引用，路由守卫里再动态 import 即可按需加载。
 */

let app = null

export function setApp(value) {
  app = value
}

export function getApp() {
  return app
}
