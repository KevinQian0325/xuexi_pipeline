<template>
  <div class="page-shell">
    <main class="page-main">
      <section class="content-panel dashboard-panel">
        <div class="panel-header">
          <div>
            <h1>网页监听与任务执行</h1>
            <p>管理监听配置，查看近期任务结果</p>
          </div>
          <div class="toolbar-actions">
            <label class="search-box">
              <span>⌕</span>
              <input
                v-model.trim="keyword"
                type="search"
                placeholder="搜索备注或网页地址..."
              />
            </label>
          </div>
        </div>

        <div class="section-tabs">
          <button
            type="button"
            :class="{ 'is-active': activeSection === 'listener' }"
            @click="activeSection = 'listener'"
          >
            网页监听配置
          </button>
          <button
            type="button"
            :class="{ 'is-active': activeSection === 'tasks' }"
            @click="activeSection = 'tasks'"
          >
            任务执行情况
          </button>
        </div>

        <div v-if="activeSection === 'listener'" class="dashboard-section">
          <div class="section-bar">
            <div>
              <h2>网页监听配置</h2>
              <p>每页最多显示 6 条监听配置</p>
            </div>
            <div class="section-actions">
              <button
                class="config-button"
                type="button"
                title="密钥配置"
                @click="openEnvConfigModal"
              >
                ⚙
              </button>
              <button class="primary-button" type="button" @click="openCreateModal">
                新增
              </button>
              <button
                class="run-button"
                type="button"
                :disabled="runningSites"
                @click="runEnabledSites"
              >
                {{ runningSites ? "运行中..." : "运行" }}
              </button>
            </div>
          </div>

          <div class="table-wrapper compact-table-wrapper">
            <table class="site-table listener-table">
              <thead>
                <tr>
                  <th>序号</th>
                  <th>备注</th>
                  <th>网页地址</th>
                  <th>爬取时间范围</th>
                  <th>状态</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody v-if="rows.length > 0">
                <tr v-for="row in pagedRows" :key="row.id">
                  <td>{{ row.index }}</td>
                  <td>
                    <div class="remark-cell">
                      <strong>{{ row.remark }}</strong>
                      <small>更新于 {{ row.updatedAt }}</small>
                    </div>
                  </td>
                  <td>
                    <a class="url-link" :href="row.pageUrl" target="_blank" rel="noreferrer">
                      {{ row.pageUrl }}
                    </a>
                  </td>
                  <td>{{ formatRange(row.startDate, row.endDate) }}</td>
                  <td>
                    <button
                      class="status-pill"
                      :class="row.enabled ? 'is-enabled' : 'is-disabled'"
                      type="button"
                      @click="toggleStatus(row)"
                    >
                      {{ row.enabled ? "启用" : "停用" }}
                    </button>
                  </td>
                  <td class="operation-cell">
                    <button class="gear-button" type="button" @click="toggleMenu(row.id)">
                      ⚙
                    </button>
                    <div v-if="activeMenuId === row.id" class="dropdown-menu">
                      <button type="button" @click="openRemarkModal(row)">修改备注</button>
                      <button type="button" @click="openTimeRangeModal(row)">设定时间范围</button>
                      <div class="dropdown-divider"></div>
                      <button class="danger-text" type="button" @click="removeRow(row.id)">
                        删除
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
              <tbody v-else>
                <tr>
                  <td colspan="6">
                    <div class="empty-state">
                      <p>暂无监听配置</p>
                      <small>可以点击“新增”创建第一个网页监听配置。</small>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-if="totalPages > 1" class="pagination-bar compact-pagination">
            <button
              class="page-button"
              type="button"
              :disabled="currentPage === 1"
              @click="goToPage(currentPage - 1)"
            >
              上一页
            </button>

            <button
              v-for="page in totalPages"
              :key="page"
              class="page-button"
              :class="{ 'is-active': page === currentPage }"
              type="button"
              @click="goToPage(page)"
            >
              {{ page }}
            </button>

            <button
              class="page-button"
              type="button"
              :disabled="currentPage === totalPages"
              @click="goToPage(currentPage + 1)"
            >
              下一页
            </button>
          </div>
        </div>

        <div v-if="activeSection === 'tasks'" class="dashboard-section">
          <div class="section-bar">
            <div>
              <h2>任务执行情况</h2>
              <p>每页最多显示 6 条网页任务</p>
            </div>
          </div>

          <div class="table-wrapper compact-table-wrapper">
          <table class="site-table execution-table">
            <thead>
              <tr>
                <th>序号</th>
                <th>备注</th>
                <th>网页地址</th>
                <th>结果目录</th>
                <th>执行状态</th>
                <th>执行时间</th>
                <th>耗时</th>
                <th>详情</th>
              </tr>
            </thead>
            <tbody v-if="taskRows.length > 0">
              <tr v-for="row in pagedTaskRows" :key="row.id">
                <td>{{ row.index }}</td>
                <td>
                  <strong>{{ row.remark }}</strong>
                </td>
                <td>
                  <a class="url-link" :href="row.pageUrl" target="_blank" rel="noreferrer">
                    {{ row.pageUrl }}
                  </a>
                </td>
                <td>
                  <a
                    v-if="canEditServerPaths && row.resultDir"
                    class="view-button"
                    :href="toHref(row.resultDir)"
                    target="_blank"
                    rel="noreferrer"
                  >
                    查看
                  </a>
                  <span
                    v-else-if="row.resultDir"
                    class="server-machine-text"
                  >
                    非服务器机器
                  </span>
                  <span v-else class="muted-text">暂无</span>
                </td>
                <td>
                  <span class="status-tag" :class="runStatusClass(row.status)">
                    {{ formatRunStatus(row.status) }} {{ row.successCount }}/{{ row.totalCount }} 条
                  </span>
                </td>
                <td>{{ row.executedAt }}</td>
                <td>{{ row.duration }}</td>
                <td>
                  <button class="secondary-action-button" type="button" @click="openTaskDetail(row)">
                    查看
                  </button>
                </td>
              </tr>
            </tbody>
            <tbody v-else>
              <tr>
                <td colspan="8">
                  <div class="empty-state">
                    <p>暂无执行记录</p>
                    <small>运行爬取任务后会在这里查看每个网页的执行情况。</small>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
          </div>

          <div v-if="taskTotalPages > 1" class="pagination-bar compact-pagination">
            <button
              class="page-button"
              type="button"
              :disabled="taskCurrentPage === 1"
              @click="goToTaskPage(taskCurrentPage - 1)"
            >
              上一页
            </button>

            <button
              v-for="page in taskTotalPages"
              :key="page"
              class="page-button"
              :class="{ 'is-active': page === taskCurrentPage }"
              type="button"
              @click="goToTaskPage(page)"
            >
              {{ page }}
            </button>

            <button
              class="page-button"
              type="button"
              :disabled="taskCurrentPage === taskTotalPages"
              @click="goToTaskPage(taskCurrentPage + 1)"
            >
              下一页
            </button>
          </div>
        </div>
      </section>
    </main>

    <ListenerSiteFormModal
      v-if="modalState === 'create'"
      mode="create"
      @close="closeModal"
      @submit="createRow"
    />

    <EnvConfigModal
      v-if="modalState === 'env-config'"
      :initial-value="envConfig"
      :can-edit-server-paths="canEditServerPaths"
      @close="closeModal"
      @submit="saveEnvConfig"
    />

    <ListenerSiteFormModal
      v-if="modalState === 'remark' && currentRow"
      mode="remark"
      :initial-value="currentRow"
      @close="closeModal"
      @submit="updateRemark"
    />

    <TimeRangeModal
      v-if="modalState === 'time-range' && currentRow"
      :initial-start-date="currentRow.startDate"
      :initial-end-date="currentRow.endDate"
      @close="closeModal"
      @submit="updateTimeRange"
    />

    <TaskExecutionDetailModal
      v-if="selectedTaskRun"
      :run="selectedTaskRun"
      :retrying="retryingRunId === selectedTaskRun.id"
      :can-open-server-paths="canEditServerPaths"
      @close="selectedTaskRunId = null"
      @rerun-failed="rerunFailedVideos"
    />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue"
import EnvConfigModal from "./components/EnvConfigModal.vue"
import ListenerSiteFormModal from "./components/ListenerSiteFormModal.vue"
import TaskExecutionDetailModal from "./components/TaskExecutionDetailModal.vue"
import TimeRangeModal from "./components/TimeRangeModal.vue"
import {
  createListenerSite,
  deleteListenerSite,
  listListenerSites,
  updateListenerSiteRemark,
  updateListenerSiteStatus,
  updateListenerSiteTimeRange,
} from "./api/listenerSites"
import { getEnvConfig, updateEnvConfig } from "./api/envConfig"
import { listTaskRuns, rerunFailedTaskVideos, startListenerSiteRun } from "./api/taskRuns"
import { formatRunStatus } from "./utils/statusLabels"
import { isServerHostAccess } from "./utils/serverAccess"

const rows = ref([])
const taskRows = ref([])
const envConfig = ref({
  xuexiAppId: "",
  xuexiAccessToken: "",
  resultFilesDir: "结果文件夹",
})
const keyword = ref("")
const activeSection = ref("listener")
const activeMenuId = ref(null)
const modalState = ref(null)
const currentRowId = ref(null)
const selectedTaskRunId = ref(null)
const retryingRunId = ref(null)
const runningSites = ref(false)
const currentPage = ref(1)
const taskCurrentPage = ref(1)
const pageSize = 6
const taskPageSize = 6
const canEditServerPaths = isServerHostAccess()

const currentRow = computed(() =>
  rows.value.find((item) => item.id === currentRowId.value) ?? null,
)

const selectedTaskRun = computed(() =>
  taskRows.value.find((item) => item.id === selectedTaskRunId.value) ?? null,
)

const totalPages = computed(() => Math.max(1, Math.ceil(rows.value.length / pageSize)))

const pagedRows = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return rows.value.slice(start, start + pageSize)
})

const taskTotalPages = computed(() =>
  Math.max(1, Math.ceil(taskRows.value.length / taskPageSize)),
)

const pagedTaskRows = computed(() => {
  const start = (taskCurrentPage.value - 1) * taskPageSize
  return taskRows.value.slice(start, start + taskPageSize)
})

onMounted(() => {
  loadRows()
  loadTaskRows()
  loadEnvConfig()
})

onBeforeUnmount(() => {
  clearTaskRefreshTimer()
})

watch(keyword, () => {
  currentPage.value = 1
  clearTimeout(searchTimer)
  searchTimer = setTimeout(loadRows, 180)
})

async function loadRows() {
  const response = await listListenerSites(keyword.value)
  rows.value = response.items
  currentPage.value = Math.min(currentPage.value, Math.max(1, Math.ceil(response.items.length / pageSize)))
}

async function loadTaskRows() {
  const response = await listTaskRuns()
  taskRows.value = response.items
  taskCurrentPage.value = Math.min(
    taskCurrentPage.value,
    Math.max(1, Math.ceil(response.items.length / taskPageSize)),
  )
  scheduleTaskRefreshIfRunning()
}

async function loadEnvConfig() {
  envConfig.value = await getEnvConfig()
}

async function createRow(payload) {
  await createListenerSite(payload)
  await loadRows()
  closeModal()
}

async function saveEnvConfig(payload) {
  await updateEnvConfig(payload)
  await loadEnvConfig()
  closeModal()
}

async function updateRemark(payload) {
  if (!currentRow.value) return
  await updateListenerSiteRemark(currentRow.value.id, payload.remark)
  await loadRows()
  closeModal()
}

async function updateTimeRange(payload) {
  if (!currentRow.value) return
  await updateListenerSiteTimeRange(
    currentRow.value.id,
    payload.startDate,
    payload.endDate,
  )
  await loadRows()
  closeModal()
}

async function toggleStatus(row) {
  await updateListenerSiteStatus(row.id, !row.enabled)
  await loadRows()
}

async function removeRow(id) {
  const confirmed = window.confirm("删除后仅移除监听配置，历史结果文件不会自动删除。是否继续？")
  if (!confirmed) return
  await deleteListenerSite(id)
  activeMenuId.value = null
  await loadRows()
}

async function runEnabledSites() {
  if (runningSites.value || taskRows.value.some((item) => item.status === "RUNNING")) {
    window.alert("当前已有运行中的任务，请等待任务完成后再运行。")
    return
  }

  const latestEnvConfig = await getEnvConfig()
  envConfig.value = latestEnvConfig
  if (!latestEnvConfig.xuexiAppId || !latestEnvConfig.xuexiAccessToken) {
    window.alert("请先配置密钥。")
    openEnvConfigModal()
    return
  }

  const response = await listListenerSites("")
  const enabledSites = response.items.filter((item) => item.enabled)

  if (enabledSites.length === 0) {
    window.alert("当前没有启用的网页监听配置。")
    return
  }

  const confirmed = window.confirm(
    `即将运行 ${enabledSites.length} 个已启用的网站，并按照各自的爬取时间范围执行。是否继续？`,
  )
  if (!confirmed) return

  runningSites.value = true
  try {
    await startListenerSiteRun(enabledSites)
    await loadTaskRows()
    activeSection.value = "tasks"
    taskCurrentPage.value = 1
  } finally {
    runningSites.value = false
  }
}

function openCreateModal() {
  modalState.value = "create"
}

function openEnvConfigModal() {
  modalState.value = "env-config"
}

function openRemarkModal(row) {
  currentRowId.value = row.id
  activeMenuId.value = null
  modalState.value = "remark"
}

function openTimeRangeModal(row) {
  currentRowId.value = row.id
  activeMenuId.value = null
  modalState.value = "time-range"
}

function closeModal() {
  modalState.value = null
  currentRowId.value = null
}

function toggleMenu(id) {
  activeMenuId.value = activeMenuId.value === id ? null : id
}

function goToPage(page) {
  currentPage.value = page
}

function goToTaskPage(page) {
  taskCurrentPage.value = page
}

function openTaskDetail(row) {
  selectedTaskRunId.value = row.id
}

async function rerunFailedVideos(runId) {
  retryingRunId.value = runId
  try {
    await rerunFailedTaskVideos(runId)
    await loadTaskRows()
  } finally {
    retryingRunId.value = null
  }
}

function runStatusClass(status) {
  if (status === "SUCCESS") return "is-success"
  if (status === "FAILED") return "is-error"
  if (status === "PARTIAL_FAILED") return "is-warning"
  return "is-progress"
}

function toHref(path) {
  if (/^https?:\/\//i.test(path)) return path
  return `file://${path}`
}

function formatRange(startDate, endDate) {
  if (!startDate && !endDate) return "从最早内容到最新内容"
  if (!startDate && endDate) return `最早内容 - ${endDate}`
  if (startDate && !endDate) return `${startDate} - 最新内容`
  return `${startDate} - ${endDate}`
}

let searchTimer = null
let taskRefreshTimer = null

function clearTaskRefreshTimer() {
  if (taskRefreshTimer) {
    clearTimeout(taskRefreshTimer)
    taskRefreshTimer = null
  }
}

function scheduleTaskRefreshIfRunning() {
  clearTaskRefreshTimer()
  if (!taskRows.value.some((item) => item.status === "RUNNING")) return

  taskRefreshTimer = setTimeout(() => {
    loadTaskRows()
  }, 5000)
}
</script>
