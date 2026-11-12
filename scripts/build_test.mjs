/**
 * 构建一份「相对路径 + 关闭 modulePreload」的产物，专供 scripts/dom_check.mjs 在 jsdom 里跑。
 *
 * 为什么要单独构建：
 *  1. 生产 dist 用绝对基址 `/`，jsdom 用 file:// 读 index.html 时动态 import 会解析成
 *     file:///D:/assets/x.js → 找不到文件；`base: './'` 得到相对路径即可。
 *  2. Vite 的 modulePreload 会插入 <link rel="modulepreload"> 并等待 load 事件，
 *     jsdom 不会真的加载这些 link，懒加载路由就会一直 pending（#app 只剩 <!---->）。
 *     关掉 modulePreload 后动态 import 走裸 ESM，jsdom 能正常解析。
 *
 * 生产产物仍由 `npm run build` 生成（绝对基址，支持 /admin/users 这种深层路由刷新）。
 */

import path from 'node:path'
import { createRequire } from 'node:module'
import { pathToFileURL } from 'node:url'

const frontend = path.resolve(import.meta.dirname, '..', 'frontend')
// 依赖装在 frontend/node_modules 里，脚本在 scripts/ 下，必须显式解析
const require = createRequire(path.join(frontend, 'package.json'))
const { build } = await import(pathToFileURL(require.resolve('vite')).href)

await build({
  root: frontend,
  configFile: path.join(frontend, 'vite.config.js'),
  base: './',
  build: {
    outDir: 'dist-test',
    emptyOutDir: true,
    modulePreload: false,
  },
})

console.log('dist-test 构建完成（base=./, modulePreload=false）')
