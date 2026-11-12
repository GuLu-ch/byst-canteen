<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import {
  NAlert,
  NButton,
  NCheckbox,
  NDivider,
  NIcon,
  NInput,
  NModal,
  NSelect,
  NSkeleton,
  NTag,
  NUpload,
  useDialog,
  useMessage,
} from 'naive-ui'
import {
  AddOutline,
  ArrowBackOutline,
  ArrowForwardOutline,
  CloseOutline,
  CloudUploadOutline,
  CopyOutline,
  DownloadOutline,
  PencilOutline,
  TrashOutline,
} from '@vicons/ionicons5'
import { api, downloadBlob } from '../api/client'
import { MEAL_LABELS, MEALS, addDays, diffDays, todayISO, weekStartOf } from '../utils/date'

const message = useMessage()
const dialog = useDialog()

const weekStart = ref(weekStartOf(todayISO()))
const loading = ref(true)
const days = ref([])
const saving = ref(false)

const DISH_TYPES = ['主食', '荤菜', '素菜', '汤品', '小菜', '凉菜', '其他']
const WEEKDAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

// 标签来自独立表 /menus/dish-tags；菜单里存的始终是原始字符串
const dishTags = ref([])

const dishOptions = computed(() =>
  dishTags.value.map((tag) => ({ label: tag.name, value: tag.name })),
)

// n-select 的 filterable 只做过滤，不再用 tag 自动建标签
// （中文输入法逐字上屏时会触发多次 create，导致 y/yi/yin 这类脏标签）
function filterTagOption(pattern, option) {
  return (option.label || '').toLowerCase().includes((pattern || '').toLowerCase())
}

const newTagName = ref('')

async function loadTags() {
  try {
    const data = await api.get('/menus/dish-tags', undefined, 'admin')
    dishTags.value = data || []
  } catch (error) {
    // 失败时退回内置标签，不影响编辑
    dishTags.value = DISH_TYPES.map((name) => ({ id: 0, name }))
  }
}

/** 显式「回车 / 点添加」才创建标签；输入法上屏时的那次回车会被忽略 */
async function addTag(event) {
  if (event?.isComposing) return // 中文输入法选词时的回车不算
  const name = newTagName.value.trim()
  if (!name) return
  if (name.length > 20) {
    message.warning('标签最多 20 个字')
    return
  }
  const existing = dishTags.value.find((tag) => tag.name === name)
  if (existing) {
    message.info(`标签「${name}」已存在`)
    newTagName.value = ''
    return
  }
  try {
    const created = await api.post('/menus/dish-tags', { name }, 'admin')
    dishTags.value = [...dishTags.value, { id: created.id, name: created.name }]
    newTagName.value = ''
    message.success(`已添加标签「${created.name}」`)
  } catch (error) {
    message.error(error.message)
  }
}

/** 删除标签：只影响之后的选项列表，已有菜单不受影响（需确认） */
function confirmRemoveTag(tag) {
  dialog.warning({
    title: '删除标签',
    content: `确定删除标签「${tag.name}」吗？已保存的菜单不会被改动，只是之后的下拉里不再出现。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await api.del(`/menus/dish-tags/${tag.id}`, 'admin')
        dishTags.value = dishTags.value.filter((item) => item.id !== tag.id)
        message.success(`标签「${tag.name}」已删除，已有菜单不受影响`)
      } catch (error) {
        message.error(error.message)
      }
    },
  })
}

const editor = reactive({ show: false, date: '', meal: 'lunch', dishes: [], note: '' })
const copyState = reactive({ show: false, from: '', to: '', overwrite: false })
const importState = reactive({ show: false, file: null, result: null, uploading: false })

const weekLabel = computed(() => `${weekStart.value.slice(5)} ~ ${addDays(weekStart.value, 6).slice(5)}`)

/** 本周 / 上周 / 下周，跟在日期区间后面显示成「11-09 ~ 11-15（本周）」 */
const weekTag = computed(() => {
  const offset = diffDays(weekStartOf(todayISO()), weekStart.value) / 7
  if (offset === 0) return '本周'
  if (offset === -1) return '上周'
  if (offset === 1) return '下周'
  return ''
})

/** 只有切到别的周时才显示「回到本周」按钮 */
const isCurrentWeek = computed(() => weekTag.value === '本周')

const weekDays = computed(() => {
  const list = []
  for (let i = 0; i < 7; i += 1) {
    const date = addDays(weekStart.value, i)
    list.push({ date, weekday: i, data: days.value.find((day) => day.date === date) })
  }
  return list
})

const totalDishes = computed(() =>
  weekDays.value.reduce(
    (sum, day) => sum + MEALS.reduce((inner, meal) => inner + dishesOf(day, meal).length, 0),
    0,
  ),
)

const filledMeals = computed(() =>
  weekDays.value.reduce(
    (sum, day) => sum + MEALS.filter((meal) => dishesOf(day, meal).length > 0).length,
    0,
  ),
)




const MEAL_META = {
  breakfast: { label: '早餐', dot: 'amber' },
  lunch: { label: '午餐', dot: 'green' },
  dinner: { label: '晚餐', dot: 'violet' },
}

async function load() {
  loading.value = true
  try {
    const data = await api.get('/menus/week', { week_start: weekStart.value }, 'admin')
    days.value = data.days || []
  } catch (error) {
    message.error(error.message)
  } finally {
    loading.value = false
  }
}

function shiftWeek(offset) {
  weekStart.value = addDays(weekStart.value, offset * 7)
  load()
}

function thisWeek() {
  weekStart.value = weekStartOf(todayISO())
  load()
}

function dishesOf(day, meal) {
  return day?.data?.meals?.[meal]?.dishes || []
}

function noteOf(day, meal) {
  return day?.data?.meals?.[meal]?.note || ''
}

function openEditor(date, meal, day) {
  const menu = day?.data?.meals?.[meal]
  editor.date = date
  editor.meal = meal
  editor.dishes = (menu?.dishes || []).map((dish) => ({ name: dish.name, type: dish.type || '其他' }))
  if (!editor.dishes.length) editor.dishes = [{ name: '', type: '荤菜' }]
  editor.note = menu?.note || ''
  editor.show = true
}

function addDish() {
  editor.dishes.push({ name: '', type: '荤菜' })
}

function removeDish(index) {
  editor.dishes.splice(index, 1)
  if (!editor.dishes.length) addDish()
}

async function saveMenu() {
  const dishes = editor.dishes
    .filter((dish) => dish.name.trim())
    .map((dish) => ({ name: dish.name.trim(), type: (dish.type || '其他').trim() || '其他' }))
  if (!dishes.length) {
    message.warning('至少填写一道菜')
    return
  }
  saving.value = true
  try {
    await api.put(`/menus/${editor.date}/${editor.meal}`, { dishes, note: editor.note }, 'admin')
    message.success('菜单已保存')
    editor.show = false
    await load()
  } catch (error) {
    message.error(error.message)
  } finally {
    saving.value = false
  }
}

async function clearMenu() {
  saving.value = true
  try {
    await api.del(`/menus/${editor.date}/${editor.meal}`, 'admin')
    message.success('已清空该餐菜单')
    editor.show = false
    await load()
  } catch (error) {
    message.error(error.message)
  } finally {
    saving.value = false
  }
}

function openCopy() {
  copyState.from = addDays(weekStart.value, -7)
  copyState.to = weekStart.value
  copyState.overwrite = false
  copyState.show = true
}

async function doCopy() {
  try {
    const result = await api.post(
      `/menus/copy?from_week=${copyState.from}&to_week=${copyState.to}&overwrite=${copyState.overwrite}`,
      undefined,
      'admin',
    )
    message.success(`已复制 ${result.copied} 餐，跳过 ${result.skipped} 餐`)
    copyState.show = false
    await load()
  } catch (error) {
    message.error(error.message)
  }
}

async function downloadTemplate() {
  try {
    const blob = await api.blob('/menus/template', { week_start: weekStart.value }, 'admin')
    downloadBlob(blob, `菜单模板_${weekStart.value}.xlsx`)
    message.success('模板已下载，可直接在表格里填写')
  } catch (error) {
    message.error(error.message)
  }
}

function onFileChange({ file }) {
  importState.file = file.file || null
  importState.result = null
  return false
}

async function doImport() {
  if (!importState.file) {
    message.warning('请先选择 Excel 文件')
    return
  }
  const form = new FormData()
  form.append('file', importState.file)
  importState.uploading = true
  try {
    const result = await api.upload('/menus/import', form, 'admin')
    importState.result = result
    message.success(`已导入 ${result.menus} 餐 / ${result.dishes} 道菜`)
    await load()
  } catch (error) {
    message.error(error.message)
  } finally {
    importState.uploading = false
  }
}

onMounted(() => {
  load()
  loadTags()
})
</script>

<template>
  <div class="admin-page">
    <header class="page-head">
      <div>
        <h2>菜单管理</h2>
        <p>按周维护每天三餐，员工端实时同步</p>
      </div>
      <div class="page-actions">
        <n-button size="small" @click="openCopy">
          <template #icon><n-icon :component="CopyOutline" /></template>
          复制上周
        </n-button>
        <n-button size="small" @click="downloadTemplate">
          <template #icon><n-icon :component="DownloadOutline" /></template>
          导出模板
        </n-button>
        <n-button size="small" type="primary" @click="importState.show = true">
          <template #icon><n-icon :component="CloudUploadOutline" /></template>
          导入菜单
        </n-button>
      </div>
    </header>

    <section class="board-toolbar">
      <div class="week-nav">
        <button class="nav-btn" type="button" title="上一周" @click="shiftWeek(-1)">
          <n-icon :size="14"><ArrowBackOutline /></n-icon>
        </button>
        <div class="week-label">
          <strong>{{ weekLabel }}<em v-if="weekTag">（{{ weekTag }}）</em></strong>
          <span>共 {{ totalDishes }} 道菜 · 已排 {{ filledMeals }} / {{ 5 * MEALS.length }} 餐</span>
        </div>
        <button class="nav-btn" type="button" title="下一周" @click="shiftWeek(1)">
          <n-icon :size="14"><ArrowForwardOutline /></n-icon>
        </button>
        <button v-if="!isCurrentWeek" class="text-btn" type="button" @click="thisWeek">回到本周</button>
      </div>
      <span class="weekend-tip">周六日不供餐</span>
    </section>

    <n-skeleton v-if="loading" text :repeat="8" />
    <div v-else class="board">
      <article
        v-for="day in weekDays"
        :key="day.date"
        class="day-card"
        :class="{ weekend: day.weekday >= 5, today: day.date === todayISO() }"
      >
        <header class="day-head">
          <div class="day-name">
            <strong>{{ WEEKDAYS[day.weekday] }}</strong>
            <span>{{ day.date.slice(5).replace('-', '.') }}</span>
          </div>
          <span v-if="day.date === todayISO()" class="today-tag">今天</span>
        </header>

        <div v-if="day.weekday >= 5" class="weekend-body">
          <span class="weekend-dot"></span>
          休息日
        </div>

        <template v-else>
          <button
            v-for="meal in MEALS"
            :key="meal"
            class="meal-block"
            type="button"
            @click="openEditor(day.date, meal, day)"
          >
            <div class="meal-head">
              <span class="meal-name">
                <i class="dot" :class="MEAL_META[meal].dot"></i>
                {{ MEAL_META[meal].label }}
                <em v-if="noteOf(day, meal)">备注</em>
              </span>
              <span class="meal-action">
                {{ dishesOf(day, meal).length ? dishesOf(day, meal).length + ' 道' : '未排' }}
                <n-icon :size="12" :component="PencilOutline" />
              </span>
            </div>

            <ul v-if="dishesOf(day, meal).length" class="dish-list">
              <li v-for="dish in dishesOf(day, meal)" :key="dish.name" class="dish-row">
                <span class="dish-name">{{ dish.name }}</span>
                <span class="dish-type">{{ dish.type }}</span>
              </li>
            </ul>
            <div v-else class="dish-empty">＋ 添加菜品</div>
          </button>
        </template>
      </article>
    </div>

    <!-- 编辑弹窗 -->
    <n-modal
      v-model:show="editor.show"
      preset="card"
      style="width: 580px"
      :bordered="false"
      :title="`${editor.date} ${MEAL_LABELS[editor.meal]}`"
    >
      <div class="editor">
        <div v-for="(dish, index) in editor.dishes" :key="index" class="editor-row">
          <span class="editor-index">{{ index + 1 }}</span>
          <n-input v-model:value="dish.name" placeholder="菜名，例如 红烧肉" size="small" />
          <n-select
            v-model:value="dish.type"
            :options="dishOptions"
            :filter="filterTagOption"
            size="small"
            style="width: 118px"
            filterable
            placeholder="类型"
            :consistent-menu-width="false"
          />
          <button class="row-del" type="button" title="删除" @click="removeDish(index)">
            <n-icon :size="14"><TrashOutline /></n-icon>
          </button>
        </div>

        <div class="tag-manager">
          <span class="tag-title">类型标签</span>
          <span v-for="tag in dishTags" :key="tag.id" class="tag-item">
            {{ tag.name }}
            <button class="tag-del" type="button" :title="`删除标签 ${tag.name}`" @click="confirmRemoveTag(tag)">
              <n-icon :size="10"><CloseOutline /></n-icon>
            </button>
          </span>
          <n-input
            v-model:value="newTagName"
            size="tiny"
            class="tag-input"
            placeholder="新标签，回车添加"
            @keyup.enter.stop="addTag"
          />
          <n-button size="tiny" quaternary type="primary" @click="addTag">添加</n-button>
        </div>

        <p class="editor-hint">
          类型从上面的标签里选；要新增类型，在「新标签，回车添加」里输入后按回车（输入法上屏完成再回车）。点标签上的 × 可删除（需确认），删除只影响之后的下拉选项，已保存的菜单不受影响。
        </p>

        <div class="editor-extra">
          <n-button size="small" dashed @click="addDish">
            <template #icon><n-icon :component="AddOutline" /></template>
            添加一道菜
          </n-button>
          <n-button size="small" quaternary type="error" @click="clearMenu">清空该餐</n-button>
        </div>

        <n-divider style="margin: 16px 0 12px" />
        <n-input
          v-model:value="editor.note"
          type="textarea"
          size="small"
          placeholder="备注，例如「有清真窗口」"
          :rows="2"
        />
      </div>
      <template #footer>
        <div class="modal-footer">
          <n-button size="small" @click="editor.show = false">取消</n-button>
          <n-button size="small" type="primary" :loading="saving" @click="saveMenu">保存菜单</n-button>
        </div>
      </template>
    </n-modal>

    <!-- 复制周 -->
    <n-modal v-model:show="copyState.show" preset="card" style="width: 420px" :bordered="false" title="复制整周菜单">
      <div class="copy-form">
        <label>
          <span>源周起始日期</span>
          <n-input v-model:value="copyState.from" size="small" placeholder="YYYY-MM-DD" />
        </label>
        <label>
          <span>目标周起始日期</span>
          <n-input v-model:value="copyState.to" size="small" placeholder="YYYY-MM-DD" />
        </label>
        <n-checkbox v-model:checked="copyState.overwrite">覆盖目标周已有菜单</n-checkbox>
      </div>
      <template #footer>
        <div class="modal-footer">
          <n-button size="small" @click="copyState.show = false">取消</n-button>
          <n-button size="small" type="primary" @click="doCopy">开始复制</n-button>
        </div>
      </template>
    </n-modal>

    <!-- 导入菜单 -->
    <n-modal v-model:show="importState.show" preset="card" style="width: 540px" :bordered="false" title="导入菜单">
      <div class="upload-box">
        <n-upload :default-upload="false" :max="1" accept=".xlsx" @change="onFileChange">
          <n-button size="small">选择 Excel 文件</n-button>
        </n-upload>
        <ul class="upload-tip">
          <li>先点「导出模板」，模板会带出本周已有菜单，直接在格子里改；</li>
          <li>早餐 5 行、午餐 6 行、晚餐 5 行，菜多时可以在该餐里插入新行；</li>
          <li>同一天同一餐的多行会整体替换原菜单，周六日自动跳过。</li>
        </ul>
      </div>

      <n-alert v-if="importState.result" type="success" :bordered="false" style="margin-top: 12px">
        已导入 {{ importState.result.menus }} 餐 / {{ importState.result.dishes }} 道菜
        <span class="muted tiny">（{{ importState.result.start }} ~ {{ importState.result.end }}）</span>
      </n-alert>
      <n-alert v-if="importState.result?.skipped_weekend" type="info" :bordered="false" style="margin-top: 10px">
        已跳过 {{ importState.result.skipped_weekend }} 行周末菜单
      </n-alert>
      <n-alert
        v-if="importState.result?.failed?.length"
        type="warning"
        :bordered="false"
        style="margin-top: 10px"
      >
        <div v-for="item in importState.result.failed.slice(0, 6)" :key="item.row" class="tiny">
          第 {{ item.row }} 行：{{ item.reason }}
        </div>
      </n-alert>

      <template #footer>
        <div class="modal-footer">
          <n-button size="small" @click="importState.show = false">关闭</n-button>
          <n-button size="small" type="primary" :loading="importState.uploading" @click="doImport">开始导入</n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<style scoped>
/* ── 顶部工具条 ─────────────────────────── */
.board-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 10px 14px;
  background: #fff;
  border: 1px solid #eceef2;
  border-radius: 12px;
}

.week-nav {
  display: flex;
  align-items: center;
  gap: 10px;
}

.nav-btn {
  width: 28px;
  height: 28px;
  border: 1px solid #eceef2;
  border-radius: 8px;
  background: #fff;
  color: #5b6472;
  display: grid;
  place-items: center;
  cursor: pointer;
  transition: 0.15s;
}

.nav-btn:hover {
  background: #f7f8fa;
  color: #111827;
  border-color: #dfe3e9;
}

.week-label {
  display: flex;
  flex-direction: column;
  line-height: 1.35;
  min-width: 150px;
}

.week-label strong {
  font-size: 13.5px;
  color: #111827;
  letter-spacing: 0.3px;
}

.week-label strong em {
  font-style: normal;
  font-weight: 600;
  color: #2563eb;
}

.week-label span {
  font-size: 11.5px;
  color: #9aa3af;
}

.text-btn {
  border: none;
  background: transparent;
  color: #2563eb;
  font-size: 12.5px;
  cursor: pointer;
  padding: 4px 2px;
}

.text-btn:hover {
  text-decoration: underline;
}

.weekend-tip {
  font-size: 11.5px;
  color: #a8b1bd;
}

/* ── 周看板 ─────────────────────────────── */
.board {
  display: grid;
  grid-template-columns: repeat(7, minmax(150px, 1fr));
  gap: 12px;
}

.day-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 10px 11px;
  background: #fff;
  border: 1px solid #eceef2;
  border-radius: 12px;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.day-card:hover {
  border-color: #dfe3e9;
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
}

.day-card.today {
  border-color: #c7d7fb;
  box-shadow: 0 6px 18px rgba(37, 99, 235, 0.08);
}

.day-card.weekend {
  background: #fbfbfc;
}

.day-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 2px 8px;
  border-bottom: 1px solid #f1f3f6;
}

.day-name {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.day-name strong {
  font-size: 13px;
  color: #111827;
  letter-spacing: 0.4px;
}

.day-name span {
  font-size: 11.5px;
  color: #9aa3af;
}

.today-tag {
  font-size: 10.5px;
  color: #2563eb;
  background: #eff4ff;
  border-radius: 5px;
  padding: 1px 6px;
  line-height: 16px;
}

.meal-block {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 7px;
  padding: 9px 9px 10px;
  border: 1px solid #f2f4f7;
  border-radius: 10px;
  background: #fcfcfd;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.meal-block:hover {
  background: #f8fafc;
  border-color: #e3e7ee;
}

.meal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.meal-name {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #333c49;
}

.meal-name .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex: none;
}

.dot.amber {
  background: #f0a94c;
}

.dot.green {
  background: #34a06a;
}

.dot.violet {
  background: #7c74e8;
}

.meal-name em {
  font-style: normal;
  font-size: 10px;
  color: #b07a17;
  background: #fdf6e7;
  border-radius: 4px;
  padding: 0 4px;
  line-height: 15px;
}

.meal-action {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 10.5px;
  color: #b3bcc8;
  transition: color 0.15s;
}

.meal-block:hover .meal-action {
  color: #6b7280;
}

.dish-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.dish-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 6px;
  font-size: 12px;
  line-height: 17px;
}

.dish-name {
  color: #2b3441;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dish-type {
  font-size: 10.5px;
  color: #a3abb8;
  flex: none;
}

.dish-empty {
  padding: 6px 0;
  font-size: 11.5px;
  color: #b6bfcb;
  text-align: center;
}

.meal-block:hover .dish-empty {
  color: #2563eb;
}

.weekend-body {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 36px 0;
  font-size: 12px;
  color: #b6bfcb;
}

.weekend-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #dfe3e9;
}

/* ── 弹窗 ──────────────────────────────── */
.editor {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.editor-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.editor-index {
  width: 18px;
  font-size: 11px;
  color: #b3bcc8;
  text-align: center;
  flex: none;
}

.row-del {
  width: 26px;
  height: 26px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #b3bcc8;
  display: grid;
  place-items: center;
  cursor: pointer;
  flex: none;
}

.row-del:hover {
  background: #fdeeee;
  color: #d64545;
}

.editor-extra {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 4px;
}

.editor-hint {
  margin: 8px 0 0;
  font-size: 11.5px;
  color: #a3abb8;
  line-height: 1.6;
}

/* 类型标签管理：回车即新增，点 × 删除（需确认） */
.tag-manager {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 4px;
  padding: 8px 10px;
  background: #f7f8fa;
  border-radius: 8px;
}

.tag-title {
  font-size: 11.5px;
  color: #9aa3af;
  margin-right: 2px;
}

.tag-item {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 4px 2px 8px;
  background: #fff;
  border: 1px solid #e5e9f0;
  border-radius: 999px;
  font-size: 11.5px;
  color: #3d4652;
}

.tag-del {
  width: 14px;
  height: 14px;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: #b3bcc8;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.tag-del:hover {
  background: #fdeeee;
  color: #d64545;
}

.tag-input {
  width: 132px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.copy-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.copy-form label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  color: #8b95a3;
}

.upload-tip {
  margin: 10px 0 0;
  padding-left: 16px;
  font-size: 12px;
  line-height: 1.9;
  color: #8b95a3;
}
</style>
