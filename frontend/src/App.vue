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
                v-model.trim="activeSearchKeyword"
                type="search"
                :placeholder="searchPlaceholder"
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
              <button class="secondary-button" type="button" @click="openIntegrityCheckModal">
                文件检查
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

          <div class="table-wrapper compact-table-wrapper listener-table-wrapper">
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

            <template v-for="page in paginationItems" :key="page">
              <button
                v-if="typeof page === 'number'"
                class="page-button"
                :class="{ 'is-active': page === currentPage }"
                type="button"
                @click="goToPage(page)"
              >
                {{ page }}
              </button>
              <span v-else class="page-ellipsis">...</span>
            </template>

            <button
              class="page-button"
              type="button"
              :disabled="currentPage === totalPages"
              @click="goToPage(currentPage + 1)"
            >
              下一页
            </button>

            <form class="page-jump-form" @submit.prevent="jumpToPage">
              <span>跳至</span>
              <input
                v-model="pageJump"
                type="number"
                min="1"
                :max="totalPages"
                aria-label="跳转页码"
              />
              <button class="page-button" type="submit">确定</button>
            </form>
          </div>
        </div>

        <div v-if="activeSection === 'tasks'" class="dashboard-section">
          <div class="section-bar">
            <div>
              <h2>任务执行情况</h2>
              <p>每页最多显示 6 条网页任务</p>
            </div>
            <div class="section-actions">
              <button
                v-if="!taskDeleteMode"
                class="quiet-danger-button"
                type="button"
                :disabled="taskRows.length === 0 || hasRunningTask"
                @click="enterTaskDeleteMode"
              >
                清除记录
              </button>
              <template v-else>
                <button
                  class="secondary-button compact-action-button"
                  type="button"
                  @click="cancelTaskDeleteMode"
                >
                  取消
                </button>
                <button
                  class="secondary-button compact-action-button"
                  type="button"
                  :disabled="pagedTaskRows.length === 0"
                  @click="toggleCurrentTaskPageSelection"
                >
                  {{ currentTaskPageAllSelected ? "取消全选" : "全选" }}
                </button>
                <button
                  class="quiet-danger-button"
                  type="button"
                  :disabled="selectedTaskRunIds.length === 0"
                  @click="deleteSelectedTaskRunRecords"
                >
                  清除所选 {{ selectedTaskRunIds.length }}
                </button>
                <button
                  class="quiet-danger-button"
                  type="button"
                  :disabled="taskRows.length === 0 || hasRunningTask"
                  @click="clearAllTaskRunRecords"
                >
                  清除全部
                </button>
              </template>
            </div>
          </div>

          <div v-if="taskDeleteMode" class="selection-hint">
            请选择要清除的执行记录。清除后不会删除结果文件、运行数据库和爬取日志。
          </div>

          <div class="table-wrapper compact-table-wrapper">
          <table class="site-table execution-table">
            <thead>
              <tr>
                <th>{{ taskDeleteMode ? "选择" : "序号" }}</th>
                <th>备注</th>
                <th>网页地址</th>
                <th>结果目录</th>
                <th>执行状态</th>
                <th>执行时间</th>
                <th>耗时</th>
                <th>详情</th>
              </tr>
            </thead>
            <tbody v-if="filteredTaskRows.length > 0">
              <tr v-for="row in pagedTaskRows" :key="row.id">
                <td>
                  <button
                    v-if="taskDeleteMode"
                    class="selection-box"
                    :class="{ 'is-selected': selectedTaskRunIds.includes(row.id) }"
                    type="button"
                    :aria-label="`选择第 ${row.index} 条记录`"
                    @click="toggleTaskRunSelection(row.id)"
                  >
                    <span v-if="selectedTaskRunIds.includes(row.id)">✓</span>
                  </button>
                  <template v-else>{{ row.index }}</template>
                </td>
                <td>
                  <strong>{{ row.remark }}</strong>
                </td>
                <td>
                  <a class="url-link" :href="row.pageUrl" target="_blank" rel="noreferrer">
                    {{ row.pageUrl }}
                  </a>
                </td>
                <td>
                  <button
                    v-if="canEditServerPaths && row.resultDir"
                    class="view-button"
                    type="button"
                    @click="openResultDir(row.resultDir)"
                  >
                    查看
                  </button>
                  <span
                    v-else-if="row.resultDir"
                    class="server-machine-text"
                  >
                    非服务器机器
                  </span>
                  <span v-else class="muted-text">暂无</span>
                </td>
                <td>
                  <div class="run-status-cell">
                    <span class="status-tag" :class="runStatusClass(row.status)">
                      {{ formatRunProgress(row.status, row.successCount, row.totalCount) }}
                    </span>
                    <span v-if="existingVideoCount(row) > 0" class="existing-summary-tag">
                      已存在 {{ existingVideoCount(row) }} 条
                    </span>
                  </div>
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
                    <p>{{ taskRows.length > 0 ? "暂无匹配记录" : "暂无执行记录" }}</p>
                    <small>
                      {{
                        taskRows.length > 0
                          ? "可以换一个备注或网页地址关键词再试。"
                          : "运行爬取任务后会在这里查看每个网页的执行情况。"
                      }}
                    </small>
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

            <template v-for="page in taskPaginationItems" :key="page">
              <button
                v-if="typeof page === 'number'"
                class="page-button"
                :class="{ 'is-active': page === taskCurrentPage }"
                type="button"
                @click="goToTaskPage(page)"
              >
                {{ page }}
              </button>
              <span v-else class="page-ellipsis">...</span>
            </template>

            <button
              class="page-button"
              type="button"
              :disabled="taskCurrentPage === taskTotalPages"
              @click="goToTaskPage(taskCurrentPage + 1)"
            >
              下一页
            </button>

            <form class="page-jump-form" @submit.prevent="jumpToTaskPage">
              <span>跳至</span>
              <input
                v-model="taskPageJump"
                type="number"
                min="1"
                :max="taskTotalPages"
                aria-label="跳转任务页码"
              />
              <button class="page-button" type="submit">确定</button>
            </form>
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

    <FileIntegrityCheckModal
      v-if="modalState === 'integrity-check'"
      :sites="integrityCheckSites"
      :has-running-task="hasRunningTask"
      @close="closeModal"
      @repair-started="handleIntegrityRepairStarted"
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
      @open-path="openResultDir"
      @rerun-failed="rerunFailedVideos"
      @rerun-videos="rerunSelectedFailedVideos"
      @ignore-videos="ignoreFailedVideos"
    />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue"
import EnvConfigModal from "./components/EnvConfigModal.vue"
import FileIntegrityCheckModal from "./components/FileIntegrityCheckModal.vue"
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
import { openServerPath } from "./api/localPaths"
import { clearTaskRuns, deleteTaskRuns, ignoreTaskRunVideos, listTaskRuns, rerunFailedTaskVideos, rerunTaskRunVideos, startListenerSiteRun } from "./api/taskRuns"
import { formatRunProgress } from "./utils/statusLabels"
import { buildPaginationItems, clampPage } from "./utils/pagination"
import { isServerHostAccess } from "./utils/serverAccess"

const rows = ref([])
const taskRows = ref([])
const integrityCheckSites = ref([])
const envConfig = ref({
  xuexiAppId: "",
  xuexiAccessToken: "",
  resultFilesDir: "",
})
const listenerKeyword = ref("")
const taskKeyword = ref("")
const activeSection = ref("listener")
const activeMenuId = ref(null)
const modalState = ref(null)
const currentRowId = ref(null)
const selectedTaskRunId = ref(null)
const retryingRunId = ref(null)
const runningSites = ref(false)
const taskDeleteMode = ref(false)
const selectedTaskRunIds = ref([])
const currentPage = ref(1)
const taskCurrentPage = ref(1)
const pageJump = ref("")
const taskPageJump = ref("")
const pageSize = 6
const taskPageSize = 6
const canEditServerPaths = isServerHostAccess()

const currentRow = computed(() =>
  rows.value.find((item) => item.id === currentRowId.value) ?? null,
)

const selectedTaskRun = computed(() =>
  taskRows.value.find((item) => item.id === selectedTaskRunId.value) ?? null,
)

const hasRunningTask = computed(() =>
  taskRows.value.some((item) => item.status === "RUNNING"),
)

const activeSearchKeyword = computed({
  get() {
    return activeSection.value === "tasks" ? taskKeyword.value : listenerKeyword.value
  },
  set(value) {
    if (activeSection.value === "tasks") {
      taskKeyword.value = value
      return
    }
    listenerKeyword.value = value
  },
})

const searchPlaceholder = computed(() =>
  activeSection.value === "tasks"
    ? "搜索任务备注或网页地址..."
    : "搜索监听备注或网页地址...",
)

const filteredTaskRows = computed(() => {
  const value = taskKeyword.value.trim().toLowerCase()
  if (!value) return taskRows.value

  return taskRows.value.filter((item) =>
    (item.remark || "").toLowerCase().includes(value) ||
    (item.pageUrl || "").toLowerCase() === value,
  )
})

function existingVideoCount(row) {
  return (row.details || []).filter((detail) => detail.status === "EXISTING").length
}

const totalPages = computed(() => Math.max(1, Math.ceil(rows.value.length / pageSize)))

const paginationItems = computed(() =>
  buildPaginationItems(currentPage.value, totalPages.value),
)

const pagedRows = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return rows.value.slice(start, start + pageSize)
})

const taskTotalPages = computed(() =>
  Math.max(1, Math.ceil(filteredTaskRows.value.length / taskPageSize)),
)

const taskPaginationItems = computed(() =>
  buildPaginationItems(taskCurrentPage.value, taskTotalPages.value),
)

const pagedTaskRows = computed(() => {
  const start = (taskCurrentPage.value - 1) * taskPageSize
  return filteredTaskRows.value.slice(start, start + taskPageSize)
})

const currentTaskPageAllSelected = computed(() =>
  pagedTaskRows.value.length > 0 &&
  pagedTaskRows.value.every((row) => selectedTaskRunIds.value.includes(row.id)),
)

onMounted(() => {
  loadRows()
  loadTaskRows()
  loadEnvConfig()
})

onBeforeUnmount(() => {
  clearTaskRefreshTimer()
})

watch(listenerKeyword, () => {
  currentPage.value = 1
  clearTimeout(searchTimer)
  searchTimer = setTimeout(loadRows, 180)
})

watch(taskKeyword, () => {
  taskCurrentPage.value = 1
})

watch(filteredTaskRows, () => {
  taskCurrentPage.value = Math.min(taskCurrentPage.value, taskTotalPages.value)
})

async function loadRows() {
  const response = await listListenerSites(listenerKeyword.value)
  rows.value = response.items
  currentPage.value = Math.min(currentPage.value, Math.max(1, Math.ceil(response.items.length / pageSize)))
}

async function loadTaskRows() {
  const response = await listTaskRuns()
  taskRows.value = response.items
  selectedTaskRunIds.value = selectedTaskRunIds.value.filter((id) =>
    response.items.some((item) => item.id === id),
  )
  if (response.items.length === 0) {
    taskDeleteMode.value = false
  }
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
  const oldRoot = (envConfig.value.resultFilesDir || "").trim()
  const nextRoot = (payload.resultFilesDir || "").trim()
  if (oldRoot && nextRoot && oldRoot !== nextRoot) {
    const confirmed = window.confirm(
      "更改保存根目录会迁移全部历史结果文件，并更新数据库中的文件路径。迁移期间请不要运行任务。是否继续？",
    )
    if (!confirmed) return
  }

  try {
    const response = await updateEnvConfig(payload)
    await loadEnvConfig()
    await loadTaskRows()
    closeModal()
    if (response?.migration?.changed) {
      window.alert("保存根目录已迁移完成，历史文件路径已同步更新。")
    }
  } catch (error) {
    window.alert(error.message || "保存配置失败。")
  }
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
  if (runningSites.value || hasRunningTask.value) {
    window.alert("当前已有运行中的任务，请等待任务完成后再运行。")
    return
  }

  const latestEnvConfig = await getEnvConfig()
  envConfig.value = latestEnvConfig
  if (!latestEnvConfig.xuexiAppId || !latestEnvConfig.xuexiAccessToken || !latestEnvConfig.resultFilesDir) {
    window.alert("请先配置 XUEXI_APP_ID、XUEXI_ACCESS_TOKEN 和结果文件存储根目录。")
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

async function openIntegrityCheckModal() {
  const response = await listListenerSites("")
  integrityCheckSites.value = response.items
  modalState.value = "integrity-check"
}

async function handleIntegrityRepairStarted() {
  await loadTaskRows()
  activeSection.value = "tasks"
  taskCurrentPage.value = 1
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
  currentPage.value = clampPage(page, totalPages.value)
}

function goToTaskPage(page) {
  taskCurrentPage.value = clampPage(page, taskTotalPages.value)
}

function jumpToPage() {
  if (pageJump.value === "") return
  goToPage(pageJump.value)
  pageJump.value = ""
}

function jumpToTaskPage() {
  if (taskPageJump.value === "") return
  goToTaskPage(taskPageJump.value)
  taskPageJump.value = ""
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

async function ignoreFailedVideos({ runId, ids }) {
  if (!ids.length) return
  await ignoreTaskRunVideos(runId, ids)
  await loadTaskRows()
}

async function rerunSelectedFailedVideos({ runId, ids }) {
  if (!ids.length) return
  retryingRunId.value = runId
  try {
    await rerunTaskRunVideos(runId, ids)
    await loadTaskRows()
  } finally {
    retryingRunId.value = null
  }
}

function enterTaskDeleteMode() {
  if (hasRunningTask.value) {
    window.alert("当前有运行中的任务，请等待任务完成后再清除记录。")
    return
  }

  taskDeleteMode.value = true
  selectedTaskRunIds.value = []
}

function cancelTaskDeleteMode() {
  taskDeleteMode.value = false
  selectedTaskRunIds.value = []
}

function toggleTaskRunSelection(id) {
  if (selectedTaskRunIds.value.includes(id)) {
    selectedTaskRunIds.value = selectedTaskRunIds.value.filter((item) => item !== id)
    return
  }

  selectedTaskRunIds.value = [...selectedTaskRunIds.value, id]
}

function toggleCurrentTaskPageSelection() {
  const pageIds = pagedTaskRows.value.map((row) => row.id)
  if (currentTaskPageAllSelected.value) {
    selectedTaskRunIds.value = selectedTaskRunIds.value.filter((id) => !pageIds.includes(id))
    return
  }

  selectedTaskRunIds.value = [...new Set([...selectedTaskRunIds.value, ...pageIds])]
}

async function deleteSelectedTaskRunRecords() {
  if (selectedTaskRunIds.value.length === 0) return
  if (hasRunningTask.value) {
    window.alert("当前有运行中的任务，请等待任务完成后再清除记录。")
    return
  }

  const confirmed = window.confirm(
    `将清除 ${selectedTaskRunIds.value.length} 条任务执行记录，不会删除结果文件、运行数据库和爬取日志。是否继续？`,
  )
  if (!confirmed) return

  await deleteTaskRuns(selectedTaskRunIds.value)
  selectedTaskRunId.value = null
  selectedTaskRunIds.value = []
  taskDeleteMode.value = false
  clearTaskRefreshTimer()
  await loadTaskRows()
}

async function clearAllTaskRunRecords() {
  if (taskRows.value.length === 0) return
  if (hasRunningTask.value) {
    window.alert("当前有运行中的任务，请等待任务完成后再清除记录。")
    return
  }

  const confirmed = window.confirm(
    `将清除全部 ${taskRows.value.length} 条任务执行记录，不会删除结果文件、运行数据库和爬取日志。是否继续？`,
  )
  if (!confirmed) return

  await clearTaskRuns()
  selectedTaskRunId.value = null
  selectedTaskRunIds.value = []
  taskDeleteMode.value = false
  taskCurrentPage.value = 1
  clearTaskRefreshTimer()
  await loadTaskRows()
}

async function openResultDir(path) {
  try {
    await openServerPath(path)
  } catch (error) {
    window.alert(error.message || "打开文件夹失败。")
  }
}

function runStatusClass(status) {
  if (status === "SUCCESS") return "is-success"
  if (status === "FAILED") return "is-error"
  if (status === "PARTIAL_FAILED") return "is-warning"
  return "is-progress"
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
