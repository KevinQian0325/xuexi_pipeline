<template>
  <BaseModal
    title="文件完整性检查"
    description="按后端运行数据库检查本地结果文件是否丢失。"
    size="large"
    @close="$emit('close')"
  >
    <div class="integrity-layout">
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
          :disabled="selectedIds.length === 0 || checking || repairing"
          @click="runCheck"
        >
          {{ checking ? "检查中..." : "开始检查" }}
        </button>
      </div>

      <div v-if="errorMessage" class="form-error">{{ errorMessage }}</div>

      <template v-if="result">
        <div class="integrity-summary">
          <div>
            <span>检查网页</span>
            <strong>{{ result.summary.siteCount }}</strong>
          </div>
          <div>
            <span>视频记录</span>
            <strong>{{ result.summary.videoCount }}</strong>
          </div>
          <div>
            <span>正常记录</span>
            <strong>{{ result.summary.normalCount }}</strong>
          </div>
          <div>
            <span>异常记录</span>
            <strong>{{ result.summary.issueCount }}</strong>
          </div>
          <div>
            <span>可修复</span>
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
              class="quiet-danger-button"
              type="button"
              :disabled="repairing"
              @click="runRepair"
            >
              {{ repairing ? "修复中..." : "按检查结果修复状态" }}
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
                  {{ issueKeyword ? "没有匹配的异常明细" : "没有发现文件缺失或状态不一致" }}
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

defineEmits(["close"])

const props = defineProps({
  sites: {
    type: Array,
    required: true,
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
  const confirmed = window.confirm("将按本地最高产物修复所选网页的运行数据库状态。是否继续？")
  if (!confirmed) return

  errorMessage.value = ""
  repairing.value = true
  try {
    await repairFileIntegrity(selectedIds.value)
    result.value = await checkFileIntegrity(selectedIds.value)
  } catch (error) {
    errorMessage.value = error.message || "修复失败"
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
