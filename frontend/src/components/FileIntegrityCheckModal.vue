<template>
  <BaseModal
    title="文件完整性检查"
    description="检查已生成文档的视频是否仍保留视频、音频和 Word 文档。"
    size="large"
    @close="$emit('close')"
  >
    <div class="integrity-layout">
      <div v-if="errorMessage" class="form-error">{{ errorMessage }}</div>

      <template v-if="!result">
        <div class="integrity-toolbar">
          <div>
            <strong>选择要检查的网页</strong>
            <span>已选 {{ selectedIds.length }}/{{ sites.length }}，当前筛选 {{ filteredSites.length }} 个</span>
          </div>
          <button class="secondary-button compact-action-button" type="button" @click="toggleAll">
            {{ allFilteredSelected ? "取消全选" : "全选筛选结果" }}
          </button>
        </div>

        <label class="search-box integrity-search-box">
          <span>⌕</span>
          <input
            v-model.trim="siteKeyword"
            type="search"
            placeholder="搜索网页备注或地址..."
          />
        </label>

        <div class="integrity-site-list">
          <button
            v-for="site in pagedSites"
            :key="site.id"
            class="integrity-site-row"
            :class="{ 'is-selected': selectedIds.includes(site.id) }"
            type="button"
            @click="toggleSite(site.id)"
          >
            <span class="selection-box" :class="{ 'is-selected': selectedIds.includes(site.id) }">
              <span v-if="selectedIds.includes(site.id)">✓</span>
            </span>
            <span>
              <strong>{{ site.remark }}</strong>
              <small>{{ site.pageUrl }}</small>
            </span>
          </button>
          <div v-if="pagedSites.length === 0" class="integrity-empty">没有匹配的网页</div>
        </div>

        <div v-if="filteredSites.length > sitePageSize" class="pagination-bar compact-pagination integrity-pagination">
          <button
            class="page-button"
            type="button"
            :disabled="siteCurrentPage === 1"
            @click="goToSitePage(siteCurrentPage - 1)"
          >
            上一页
          </button>
          <template v-for="page in sitePaginationItems" :key="page">
            <button
              v-if="typeof page === 'number'"
              class="page-button"
              :class="{ 'is-active': page === siteCurrentPage }"
              type="button"
              @click="goToSitePage(page)"
            >
              {{ page }}
            </button>
            <span v-else class="page-ellipsis">...</span>
          </template>
          <button
            class="page-button"
            type="button"
            :disabled="siteCurrentPage === siteTotalPages"
            @click="goToSitePage(siteCurrentPage + 1)"
          >
            下一页
          </button>
          <form class="page-jump-form" @submit.prevent="jumpToSitePage">
            <span>跳至</span>
            <input
              v-model="sitePageJump"
              type="number"
              min="1"
              :max="siteTotalPages"
              aria-label="跳转网页选择页码"
            />
            <button class="page-button" type="submit">确定</button>
          </form>
        </div>

        <div class="integrity-actions">
          <button
            class="primary-button"
            type="button"
            :disabled="selectedIds.length === 0 || checking || repairing || hasRunningTask"
            @click="runCheck"
          >
            {{ checkButtonText }}
          </button>
        </div>
      </template>

      <template v-else>
        <div class="integrity-result-top">
          <div>
            <strong>检查结果</strong>
            <span>已检查 {{ result.summary.siteCount }} 个网页，{{ result.summary.videoCount }} 条完成视频</span>
          </div>
          <button class="secondary-button compact-action-button" type="button" @click="backToSelection">
            返回重新选择
          </button>
        </div>

        <div class="integrity-summary">
          <div>
            <span>检查网页</span>
            <strong>{{ result.summary.siteCount }}</strong>
          </div>
          <div>
            <span>完成视频</span>
            <strong>{{ result.summary.videoCount }}</strong>
          </div>
          <div>
            <span>文件完整</span>
            <strong>{{ result.summary.normalCount }}</strong>
          </div>
          <div>
            <span>缺失记录</span>
            <strong>{{ result.summary.issueCount }}</strong>
          </div>
          <div>
            <span>可补齐</span>
            <strong>{{ result.summary.fixableCount }}</strong>
          </div>
        </div>

        <div class="integrity-result-header">
          <div>
            <strong>异常明细</strong>
            <span>{{ filteredIssueDetails.length }}/{{ result.details.length }} 条</span>
          </div>
          <div class="integrity-result-actions">
            <label class="search-box integrity-search-box">
              <span>⌕</span>
              <input
                v-model.trim="issueKeyword"
                type="search"
                placeholder="搜索视频名或网页备注..."
              />
            </label>
            <button
              v-if="result.summary.fixableCount > 0"
              class="primary-action-button"
              type="button"
              :disabled="repairing || hasRunningTask"
              @click="runRepair"
            >
              {{ repairButtonText }}
            </button>
          </div>
        </div>

        <div class="table-wrapper integrity-table-wrapper">
          <table class="site-table integrity-table">
            <thead>
              <tr>
                <th>网页备注</th>
                <th>视频名</th>
                <th>当前状态</th>
                <th>缺失内容</th>
                <th>说明</th>
              </tr>
            </thead>
            <tbody v-if="pagedIssueDetails.length > 0">
              <tr v-for="item in pagedIssueDetails" :key="item.id">
                <td>{{ item.siteRemark }}</td>
                <td>
                  <strong class="video-title">{{ item.videoTitle }}</strong>
                </td>
                <td>{{ item.currentStatusLabel }}</td>
                <td>{{ item.missingArtifacts.join("、") || "暂无" }}</td>
                <td>{{ item.message }}</td>
              </tr>
            </tbody>
            <tbody v-else>
              <tr>
                <td colspan="5" class="empty-detail-cell">
                  {{ issueKeyword ? "没有匹配的异常明细" : "已完成视频的本地文件都完整" }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="filteredIssueDetails.length > issuePageSize" class="pagination-bar compact-pagination integrity-pagination">
          <button
            class="page-button"
            type="button"
            :disabled="issueCurrentPage === 1"
            @click="goToIssuePage(issueCurrentPage - 1)"
          >
            上一页
          </button>
          <template v-for="page in issuePaginationItems" :key="page">
            <button
              v-if="typeof page === 'number'"
              class="page-button"
              :class="{ 'is-active': page === issueCurrentPage }"
              type="button"
              @click="goToIssuePage(page)"
            >
              {{ page }}
            </button>
            <span v-else class="page-ellipsis">...</span>
          </template>
          <button
            class="page-button"
            type="button"
            :disabled="issueCurrentPage === issueTotalPages"
            @click="goToIssuePage(issueCurrentPage + 1)"
          >
            下一页
          </button>
          <form class="page-jump-form" @submit.prevent="jumpToIssuePage">
            <span>跳至</span>
            <input
              v-model="issuePageJump"
              type="number"
              min="1"
              :max="issueTotalPages"
              aria-label="跳转异常明细页码"
            />
            <button class="page-button" type="submit">确定</button>
          </form>
        </div>
      </template>
    </div>
  </BaseModal>
</template>

<script setup>
import { computed, ref, watch } from "vue"
import BaseModal from "./BaseModal.vue"
import { checkFileIntegrity, repairFileIntegrity } from "../api/integrityCheck"
import { buildPaginationItems, clampPage } from "../utils/pagination"

const emit = defineEmits(["close", "repair-started"])

const props = defineProps({
  sites: {
    type: Array,
    required: true,
  },
  hasRunningTask: {
    type: Boolean,
    default: false,
  },
})

const sitePageSize = 6
const issuePageSize = 6
const selectedIds = ref(props.sites.map((site) => site.id))
const checking = ref(false)
const repairing = ref(false)
const errorMessage = ref("")
const result = ref(null)
const siteKeyword = ref("")
const issueKeyword = ref("")
const siteCurrentPage = ref(1)
const issueCurrentPage = ref(1)
const sitePageJump = ref("")
const issuePageJump = ref("")

const sortedSites = computed(() =>
  [...props.sites].sort((a, b) => {
    if (a.enabled !== b.enabled) return a.enabled ? -1 : 1
    return String(b.updatedAt || "").localeCompare(String(a.updatedAt || ""))
  }),
)

const filteredSites = computed(() => {
  const keyword = siteKeyword.value.trim().toLowerCase()
  if (!keyword) return sortedSites.value
  return sortedSites.value.filter((site) =>
    `${site.remark || ""} ${site.pageUrl || ""}`.toLowerCase().includes(keyword),
  )
})

const siteTotalPages = computed(() =>
  Math.max(1, Math.ceil(filteredSites.value.length / sitePageSize)),
)

const sitePaginationItems = computed(() =>
  buildPaginationItems(siteCurrentPage.value, siteTotalPages.value),
)

const pagedSites = computed(() => {
  const start = (siteCurrentPage.value - 1) * sitePageSize
  return filteredSites.value.slice(start, start + sitePageSize)
})

const allFilteredSelected = computed(() =>
  filteredSites.value.length > 0 &&
  filteredSites.value.every((site) => selectedIds.value.includes(site.id)),
)

const checkButtonText = computed(() => {
  if (checking.value) return "检查中..."
  if (props.hasRunningTask) return "任务运行中"
  return "开始检查"
})

const repairButtonText = computed(() => {
  if (repairing.value) return "创建任务中..."
  if (props.hasRunningTask) return "任务运行中"
  return "补齐缺失文件"
})

const issueDetails = computed(() => result.value?.details ?? [])

const filteredIssueDetails = computed(() => {
  const keyword = issueKeyword.value.trim().toLowerCase()
  if (!keyword) return issueDetails.value
  return issueDetails.value.filter((item) =>
    `${item.siteRemark || ""} ${item.videoTitle || ""}`.toLowerCase().includes(keyword),
  )
})

const issueTotalPages = computed(() =>
  Math.max(1, Math.ceil(filteredIssueDetails.value.length / issuePageSize)),
)

const issuePaginationItems = computed(() =>
  buildPaginationItems(issueCurrentPage.value, issueTotalPages.value),
)

const pagedIssueDetails = computed(() => {
  const start = (issueCurrentPage.value - 1) * issuePageSize
  return filteredIssueDetails.value.slice(start, start + issuePageSize)
})

function toggleSite(id) {
  result.value = null
  if (selectedIds.value.includes(id)) {
    selectedIds.value = selectedIds.value.filter((item) => item !== id)
    return
  }
  selectedIds.value = [...selectedIds.value, id]
}

function toggleAll() {
  result.value = null
  const filteredIds = filteredSites.value.map((site) => site.id)
  if (allFilteredSelected.value) {
    selectedIds.value = selectedIds.value.filter((id) => !filteredIds.includes(id))
    return
  }
  selectedIds.value = [...new Set([...selectedIds.value, ...filteredIds])]
}

function goToSitePage(page) {
  siteCurrentPage.value = clampPage(page, siteTotalPages.value)
}

function jumpToSitePage() {
  if (sitePageJump.value === "") return
  goToSitePage(sitePageJump.value)
  sitePageJump.value = ""
}

function goToIssuePage(page) {
  issueCurrentPage.value = clampPage(page, issueTotalPages.value)
}

function jumpToIssuePage() {
  if (issuePageJump.value === "") return
  goToIssuePage(issuePageJump.value)
  issuePageJump.value = ""
}

function backToSelection() {
  result.value = null
  issueKeyword.value = ""
  issueCurrentPage.value = 1
  issuePageJump.value = ""
}

async function runCheck() {
  errorMessage.value = ""
  checking.value = true
  try {
    result.value = await checkFileIntegrity(selectedIds.value)
    issueKeyword.value = ""
    issueCurrentPage.value = 1
  } catch (error) {
    errorMessage.value = error.message || "检查失败"
  } finally {
    checking.value = false
  }
}

async function runRepair() {
  if (!result.value || result.value.summary.fixableCount === 0) return
  const confirmed = window.confirm("将重新运行缺失文件的视频，补齐 mp4、wav 和 Word 文档。是否继续？")
  if (!confirmed) return

  errorMessage.value = ""
  repairing.value = true
  try {
    const response = await repairFileIntegrity(selectedIds.value)
    window.alert(response?.message || "缺失文件补齐任务已创建")
    emit("repair-started", response)
    emit("close")
  } catch (error) {
    errorMessage.value = error.message || "创建补齐任务失败"
  } finally {
    repairing.value = false
  }
}

watch(siteKeyword, () => {
  siteCurrentPage.value = 1
})

watch(siteTotalPages, (pages) => {
  if (siteCurrentPage.value > pages) {
    siteCurrentPage.value = pages
  }
})

watch(issueKeyword, () => {
  issueCurrentPage.value = 1
})

watch(issueTotalPages, (pages) => {
  if (issueCurrentPage.value > pages) {
    issueCurrentPage.value = pages
  }
})
</script>
