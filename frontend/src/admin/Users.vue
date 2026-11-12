<script setup>
import { computed, h, onMounted, reactive, ref } from 'vue'
import {
  NAlert,
  NAvatar,
  NButton,
  NCard,
  NDataTable,
  NForm,
  NFormItem,
  NIcon,
  NInput,
  NModal,
  NSelect,
  NSkeleton,
  NSwitch,
  NTag,
  NUpload,
  useDialog,
  useMessage,
} from 'naive-ui'
import { CloudUploadOutline, DownloadOutline, PersonAddOutline } from '@vicons/ionicons5'
import { api, downloadBlob } from '../api/client'

const message = useMessage()
const dialog = useDialog()

const loading = ref(true)
const rows = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const keyword = ref('')
const role = ref('')
const active = ref('')
const overview = ref(null)

const ROLE_LABELS = { admin: '管理员', cook: '厨师', employee: '员工' }
const roleOptions = [
  { label: '全部角色', value: '' },
  { label: '管理员', value: 'admin' },
  { label: '厨师', value: 'cook' },
  { label: '员工', value: 'employee' },
]
const statusOptions = [
  { label: '全部状态', value: '' },
  { label: '在职', value: 'true' },
  { label: '已停用', value: 'false' },
]

const form = reactive({
  show: false,
  mode: 'create',
  id: null,
  name: '',
  phone: '',
  username: '',
  department: '',
  role: 'employee',
  password: '',
  is_active: true,
})

const importState = reactive({ show: false, file: null, result: null, uploading: false })

const statCards = computed(() => {
  const data = overview.value
  if (!data) return []
  return [
    { label: '员工总数', value: data.total, unit: '人' },
    { label: '在职员工', value: data.active, unit: '人' },
    { label: '管理员', value: data.by_role.admin || 0, unit: '人' },
    { label: '厨师', value: data.by_role.cook || 0, unit: '人' },
    { label: '普通员工', value: data.by_role.employee || 0, unit: '人' },
  ]
})

const columns = [
  {
    title: '员工',
    key: 'name',
    minWidth: 200,
    render: (row) =>
      h('div', { style: 'display:flex;align-items:center;gap:10px' }, [
        h(
          NAvatar,
          { round: true, size: 32, color: row.is_active ? '#1f6feb' : '#c3ccd9' },
          { default: () => (row.name || '员').slice(-1) },
        ),
        h('div', null, [
          h('div', { class: 'cell-strong' }, row.name),
          h('div', { class: 'cell-sub' }, row.role === 'employee' ? row.phone : `账号 ${row.username || row.phone}`),
        ]),
      ]),
  },
  { title: '部门', key: 'department', width: 140, render: (row) => row.department || '—' },
  {
    title: '角色',
    key: 'role',
    width: 110,
    render: (row) =>
      h(
        NTag,
        {
          size: 'small',
          bordered: false,
          round: true,
          type: row.role === 'admin' ? 'error' : row.role === 'cook' ? 'warning' : 'info',
        },
        { default: () => ROLE_LABELS[row.role] || row.role },
      ),
  },
  {
    title: '口味档案',
    key: 'profile',
    minWidth: 240,
    render: (row) => {
      const tags = []
      if (row.allergens) tags.push(h('span', { class: 'chip bad' }, `忌口：${row.allergens}`))
      if (row.preferences) tags.push(h('span', { class: 'chip' }, row.preferences))
      if (row.taste) tags.push(h('span', { class: 'chip' }, row.taste))
      if (!tags.length) return h('span', { class: 'muted tiny' }, '未填写')
      return h('div', { style: 'display:flex;gap:6px;flex-wrap:wrap' }, tags)
    },
  },
  {
    title: '状态',
    key: 'is_active',
    width: 90,
    render: (row) =>
      h(
        NTag,
        { size: 'small', bordered: false, round: true, type: row.is_active ? 'success' : 'default' },
        { default: () => (row.is_active ? '在职' : '已停用') },
      ),
  },
  {
    title: '操作',
    key: 'actions',
    width: 250,
    render: (row) =>
      h('div', { style: 'display:flex;gap:4px;flex-wrap:wrap' }, [
        h(NButton, { size: 'tiny', quaternary: true, type: 'primary', onClick: () => openEdit(row) }, { default: () => '编辑' }),
        h(
          NButton,
          { size: 'tiny', quaternary: true, onClick: () => resetPassword(row) },
          { default: () => '重置密码' },
        ),
        h(
          NButton,
          {
            size: 'tiny',
            quaternary: true,
            type: row.is_active ? 'error' : 'success',
            onClick: () => toggleActive(row),
          },
          { default: () => (row.is_active ? '停用' : '启用') },
        ),
      ]),
  },
]

const pagination = computed(() => ({
  page: page.value,
  pageSize: pageSize.value,
  itemCount: total.value,
  showSizePicker: true,
  pageSizes: [10, 20, 50],
  prefix: () => `共 ${total.value} 人`,
  onUpdatePage: (value) => {
    page.value = value
    load()
  },
  onUpdatePageSize: (value) => {
    pageSize.value = value
    page.value = 1
    load()
  },
}))

async function loadOverview() {
  overview.value = await api.get('/users/overview', undefined, 'admin')
}

async function load() {
  loading.value = true
  try {
    const data = await api.get('/users', {
      q: keyword.value,
      role: role.value,
      active: active.value,
      page: page.value,
      page_size: pageSize.value,
    }, 'admin')
    rows.value = data.items
    total.value = data.total
  } catch (error) {
    message.error(error.message)
  } finally {
    loading.value = false
  }
}

function reset() {
  keyword.value = ''
  role.value = ''
  active.value = ''
  page.value = 1
  load()
}

function openCreate() {
  Object.assign(form, {
    show: true,
    mode: 'create',
    id: null,
    name: '',
    phone: '',
    username: '',
    department: '',
    role: 'employee',
    password: '',
    is_active: true,
  })
}

function openEdit(row) {
  Object.assign(form, {
    show: true,
    mode: 'edit',
    id: row.id,
    name: row.name,
    phone: row.phone,
    username: row.username || '',
    department: row.department || '',
    role: row.role,
    password: '',
    is_active: row.is_active,
  })
}

async function submit() {
  if (!form.name.trim()) {
    message.warning('请填写姓名')
    return
  }
  if (!form.phone.trim()) {
    message.warning('请填写手机号')
    return
  }
  if (!/^\d{5,20}$/.test(form.phone.trim())) {
    message.warning('手机号格式不正确')
    return
  }
  const isStaff = form.role === 'admin' || form.role === 'cook'
  if (isStaff && !form.username.trim()) {
    message.warning('管理员/厨师需要填写管理端登录账号')
    return
  }
  if (form.username.trim() && !/^[A-Za-z0-9_.-]{3,20}$/.test(form.username.trim())) {
    message.warning('账号需为 3-20 位字母、数字或 _ . - 组合')
    return
  }
  try {
    if (form.mode === 'create') {
      await api.post('/users', {
        name: form.name.trim(),
        phone: form.phone.trim(),
        username: isStaff ? form.username.trim() : '',
        department: form.department.trim(),
        role: form.role,
        password: form.password.trim(),
      }, 'admin')
      message.success(isStaff ? '管理端账号已创建' : '员工已添加，初始密码 123456')
    } else {
      const payload = {
        name: form.name.trim(),
        department: form.department.trim(),
        role: form.role,
        username: isStaff ? form.username.trim() : '',
        is_active: form.is_active,
      }
      if (form.password.trim()) payload.password = form.password.trim()
      await api.put(`/users/${form.id}`, payload, 'admin')
      message.success('已保存')
    }
    form.show = false
    await Promise.all([load(), loadOverview()])
  } catch (error) {
    message.error(error.message)
  }
}

function resetPassword(row) {
  dialog.warning({
    title: '重置密码',
    content: `确定把「${row.name}」的密码重置为 123456 吗？`,
    positiveText: '确定重置',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await api.post(`/users/${row.id}/reset-password`, undefined, 'admin')
        message.success('密码已重置为 123456')
      } catch (error) {
        message.error(error.message)
      }
    },
  })
}

function toggleActive(row) {
  if (row.is_active) {
    dialog.warning({
      title: '停用账号',
      content: `停用后「${row.name}」将无法登录，确定继续吗？`,
      positiveText: '停用',
      negativeText: '取消',
      onPositiveClick: async () => {
        try {
          await api.del(`/users/${row.id}`, 'admin')
          message.success('账号已停用')
          await Promise.all([load(), loadOverview()])
        } catch (error) {
          message.error(error.message)
        }
      },
    })
    return
  }
  api
    .put(`/users/${row.id}`, { is_active: true }, 'admin')
    .then(async () => {
      message.success('账号已启用')
      await Promise.all([load(), loadOverview()])
    })
    .catch((error) => message.error(error.message))
}

async function downloadTemplate() {
  try {
    const blob = await api.blob('/users/template', undefined, 'admin')
    downloadBlob(blob, '员工导入模板.xlsx')
    message.success('模板已下载')
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
    message.warning('请先选择文件')
    return
  }
  const data = new FormData()
  data.append('file', importState.file)
  importState.uploading = true
  try {
    const result = await api.upload('/users/import', data, 'admin')
    importState.result = result
    message.success(`导入完成：新增 ${result.created} 人，更新 ${result.updated} 人`)
    await Promise.all([load(), loadOverview()])
  } catch (error) {
    message.error(error.message)
  } finally {
    importState.uploading = false
  }
}

onMounted(() => {
  loadOverview()
  load()
})
</script>

<template>
  <div class="admin-page">
    <div class="page-head">
      <div>
        <h2>员工管理</h2>
        <p>员工用手机号登录用户端；管理员/厨师另设账号密码登录管理后台，初始密码都是 123456</p>
      </div>
      <div class="page-actions">
        <n-button size="small" @click="downloadTemplate">
          <template #icon><n-icon :component="DownloadOutline" /></template>
          下载模板
        </n-button>
        <n-button size="small" @click="importState.show = true">
          <template #icon><n-icon :component="CloudUploadOutline" /></template>
          批量导入
        </n-button>
        <n-button size="small" type="primary" @click="openCreate">
          <template #icon><n-icon :component="PersonAddOutline" /></template>
          新增员工
        </n-button>
      </div>
    </div>

    <n-skeleton v-if="!overview" height="110px" :sharp="false" />
    <div v-else class="stat-grid">
      <div v-for="item in statCards" :key="item.label" class="stat">
        <div class="stat-label">{{ item.label }}</div>
        <div class="stat-value">{{ item.value }}<small>{{ item.unit }}</small></div>
      </div>
    </div>

    <n-card :bordered="false">
      <template #header>
        <div class="panel-head">
          <div class="panel-title"><i />员工列表</div>
          <div class="toolbar">
            <n-input
              v-model:value="keyword"
              size="small"
              placeholder="搜索姓名 / 手机号 / 部门"
              clearable
              style="width: 220px"
              @keyup.enter="page = 1, load()"
            />
            <n-select v-model:value="role" :options="roleOptions" size="small" style="width: 130px" @update:value="page = 1, load()" />
            <n-select v-model:value="active" :options="statusOptions" size="small" style="width: 120px" @update:value="page = 1, load()" />
            <n-button size="small" type="primary" ghost @click="page = 1, load()">查询</n-button>
            <n-button size="small" quaternary @click="reset">重置</n-button>
          </div>
        </div>
      </template>

      <n-skeleton v-if="loading" text :repeat="6" />
      <n-data-table
        v-else
        :columns="columns"
        :data="rows"
        :bordered="false"
        size="small"
        :row-key="(row) => row.id"
        :pagination="pagination"
      />
    </n-card>

    <!-- 新增 / 编辑 -->
    <n-modal
      v-model:show="form.show"
      preset="card"
      style="width: 460px"
      :title="form.mode === 'create' ? '新增员工' : '编辑员工'"
    >
      <n-form label-placement="top" size="small">
        <n-form-item label="姓名">
          <n-input v-model:value="form.name" placeholder="例如 张伟" />
        </n-form-item>
        <n-form-item label="手机号（员工端登录账号）">
          <n-input v-model:value="form.phone" :disabled="form.mode === 'edit'" placeholder="11 位手机号" />
        </n-form-item>
        <n-form-item v-if="form.role !== 'employee'" label="管理端登录账号">
          <n-input v-model:value="form.username" placeholder="3-20 位字母、数字或 _ . -" />
          <template #feedback>管理员/厨师用这个账号 + 密码从 /admin 登录</template>
        </n-form-item>
        <n-form-item label="部门">
          <n-input v-model:value="form.department" placeholder="例如 生产部" />
        </n-form-item>
        <n-form-item label="角色">
          <n-select
            v-model:value="form.role"
            :options="[
              { label: '员工（用户端）', value: 'employee' },
              { label: '厨师（管理端）', value: 'cook' },
              { label: '管理员（管理端）', value: 'admin' },
            ]"
          />
        </n-form-item>
        <n-form-item :label="form.mode === 'create' ? '初始密码（留空为 123456）' : '重置密码（留空则不修改）'">
          <n-input v-model:value="form.password" type="password" show-password-on="click" placeholder="留空即可" />
        </n-form-item>
        <n-form-item v-if="form.mode === 'edit'" label="在职状态">
          <n-switch v-model:value="form.is_active" />
        </n-form-item>
      </n-form>
      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: 8px">
          <n-button size="small" @click="form.show = false">取消</n-button>
          <n-button size="small" type="primary" @click="submit">保存</n-button>
        </div>
      </template>
    </n-modal>

    <!-- 批量导入 -->
    <n-modal v-model:show="importState.show" preset="card" style="width: 520px" title="批量导入员工">
      <div class="upload-box">
        <n-upload :default-upload="false" :max="1" accept=".xlsx,.xlsm,.csv" @change="onFileChange">
          <n-button size="small">选择 Excel / CSV 文件</n-button>
        </n-upload>
        <div class="upload-tip">
          列顺序：姓名、手机号、部门、角色（员工/厨师/管理员）、账号（管理员/厨师必填）、初始密码（可留空，默认 123456）。<br />
          手机号已存在时会更新该员工的姓名、部门与角色。
        </div>
      </div>

      <n-alert v-if="importState.result" type="success" :bordered="false" style="margin-top: 12px">
        新增 {{ importState.result.created }} 人，更新 {{ importState.result.updated }} 人
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
        <div style="display: flex; justify-content: flex-end; gap: 8px">
          <n-button size="small" @click="importState.show = false">关闭</n-button>
          <n-button size="small" type="primary" :loading="importState.uploading" @click="doImport">开始导入</n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>
