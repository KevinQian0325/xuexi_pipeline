<template>
  <BaseModal
    title="执行明细"
    :description="`${run.remark} · ${run.executedAt}`"
    size="large"
    @close="$emit('close')"
  >
    <div class="detail-summary">
      <div>
        <span>网页地址</span>
        <a :href="run.pageUrl" target="_blank" rel="noreferrer">{{ run.pageUrl }}</a>
      </div>
      <div>
        <span>执行状态</span>
        <strong>{{ formatRunProgress(run.status, run.successCount, run.totalCount) }}</strong>
      </div>
    </div>

    <div class="detail-actions">
      <button
        v-if="ignoredDetails.length > 0"
        class="existing-toggle-button"
        :class="{ 'is-primary': showIgnored }"
        type="button"
        @click="toggleIgnoredDetails"
      >
        {{ ignoredToggleText }}
      </button>
      <button
        v-if="existingDetails.length > 0"
        class="existing-toggle-button"
        :class="{ 'is-primary': showExisting }"
        type="button"
        @click="toggleExistingDetails"
      >
        {{ existingToggleText }}
      </button>
      <button
        class="retry-button"
        :class="{ 'is-primary': showFailed }"
        type="button"
        :disabled="!hasFailedVideos"
        @click="toggleFailedDetails"
      >
        {{ failedToggleText }}
      </button>
    </div>

    <div class="detail-list-toolbar">
      <div>
        <strong>{{ currentListTitle }}</strong>
        <span>{{ filteredDetails.length }} 条</span>
      </div>
      <div class="detail-toolbar-actions">
        <template v-if="showFailed">
          <button
            v-if="!failedSelectMode"
            class="secondary-action-button"
            type="button"
            @click="enterFailedSelectMode"
          >
            选择
          </button>
          <template v-else>
            <button class="secondary-action-button" type="button" @click="selectAllFailedVideos">
              全选
            </button>
            <button class="secondary-action-button" type="button" @click="cancelFailedSelectMode">
              取消
            </button>
            <button
              class="danger-outline-button"
              type="button"
              :disabled="selectedFailedIds.length === 0"
              @click="ignoreSelectedFailedVideos"
            >
              忽略所选
            </button>
            <button
              class="primary-action-button"
              type="button"
              :disabled="selectedFailedIds.length === 0 || retrying"
              @click="rerunSelectedFailedVideos"
            >
              {{ retrying ? "正在重新运行..." : "重新运行所选" }}
            </button>
          </template>
        </template>
        <label class="search-box detail-search-box">
          <span>⌕</span>
          <input
            v-model.trim="detailKeyword"
            type="search"
            placeholder="搜索视频名..."
          />
        </label>
      </div>
    </div>

    <div class="table-wrapper detail-table-wrapper">
      <table class="site-table detail-table" :class="{ 'has-selection': showFailed && failedSelectMode }">
        <thead>
          <tr>
            <th v-if="showFailed && failedSelectMode">选择</th>
            <th>视频名</th>
            <th>视频网站</th>
            <th>视频发布时间</th>
            <th>执行时间</th>
            <th>状态</th>
            <th>文件地址</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in pagedDetails" :key="item.id">
            <td v-if="showFailed && failedSelectMode">
              <label class="row-checkbox">
                <input
                  type="checkbox"
                  :checked="selectedFailedIds.includes(item.id)"
                  @change="toggleFailedSelection(item.id)"
                />
                <span></span>
              </label>
            </td>
            <td>
              <strong class="video-title">{{ item.title }}</strong>
            </td>
            <td>
              <a
                v-if="item.detailUrl"
                class="view-button detail-link-button"
                :href="item.detailUrl"
                target="_blank"
                rel="noreferrer"
              >
                查看
              </a>
              <span v-else class="muted-text">暂无</span>
            </td>
            <td>{{ item.publishTime || "暂无" }}</td>
            <td>{{ item.executedAt }}</td>
            <td>
              <span class="status-tag" :class="statusView(item).className">
                {{ statusView(item).label }}
              </span>
            </td>
            <td>
              <button
                v-if="canOpenServerPaths && artifactTarget(item)"
                class="view-button"
                type="button"
                @click="$emit('open-path', artifactTarget(item).path)"
              >
                {{ artifactTarget(item).label }}
              </button>
              <span
                v-else-if="artifactTarget(item)"
                class="server-machine-text"
              >
                非服务器机器
              </span>
              <span v-else class="muted-text">暂无</span>
            </td>
          </tr>
          <tr v-if="pagedDetails.length === 0">
            <td :colspan="showFailed && failedSelectMode ? 7 : 6" class="empty-detail-cell">
              {{ emptyDetailText }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="filteredDetails.length > detailPageSize" class="pagination-bar compact-pagination detail-pagination">
      <button
        class="page-button"
        type="button"
        :disabled="currentPage === 1"
        @click="goToDetailPage(currentPage - 1)"
      >
        上一页
      </button>

      <template v-for="page in paginationItems" :key="page">
        <button
          v-if="typeof page === 'number'"
          class="page-button"
          :class="{ 'is-active': page === currentPage }"
          type="button"
          @click="goToDetailPage(page)"
        >
          {{ page }}
        </button>
        <span v-else class="page-ellipsis">...</span>
      </template>

      <button
        class="page-button"
        type="button"
        :disabled="currentPage === totalPages"
        @click="goToDetailPage(currentPage + 1)"
      >
        下一页
      </button>

      <form class="page-jump-form" @submit.prevent="jumpToDetailPage">
        <span>跳至</span>
        <input
          v-model="detailPageJump"
          type="number"
          min="1"
          :max="totalPages"
          aria-label="跳转明细页码"
        />
        <button class="page-button" type="submit">确定</button>
      </form>
    </div>
  </BaseModal>
</template>

<script setup>
import { computed, ref, watch } from "vue"
import BaseModal from "./BaseModal.vue"
import { formatRunProgress, getVideoStatusView } from "../utils/statusLabels"
import { buildPaginationItems, clampPage } from "../utils/pagination"

const emit = defineEmits(["close", "open-path", "rerun-failed", "rerun-videos", "ignore-videos"])

const props = defineProps({
  run: {
    type: Object,
    required: true,
  },
  retrying: {
    type: Boolean,
    default: false,
  },
  canOpenServerPaths: {
    type: Boolean,
    default: false,
  },
})

const detailPageSize = 6
const showExisting = ref(false)
const showFailed = ref(false)
const showIgnored = ref(false)
const failedSelectMode = ref(false)
const selectedFailedIds = ref([])
const detailKeyword = ref("")
const currentPage = ref(1)
const detailPageJump = ref("")

const normalDetails = computed(() =>
  props.run.details.filter((item) => item.status !== "EXISTING" && item.status !== "IGNORED"),
)

const existingDetails = computed(() =>
  props.run.details.filter((item) => item.status === "EXISTING"),
)

const ignoredDetails = computed(() =>
  props.run.details.filter((item) => item.status === "IGNORED"),
)

const failedDetails = computed(() =>
  normalDetails.value.filter((item) =>
    !["DOCX_DONE", "IGNORED", "PENDING", "PROCESSING"].includes(item.status),
  ),
)

const visibleDetails = computed(() =>
  showIgnored.value
    ? ignoredDetails.value
    : showFailed.value
    ? failedDetails.value
    : showExisting.value
      ? existingDetails.value
      : normalDetails.value,
)

const filteredDetails = computed(() => {
  const keyword = detailKeyword.value.trim().toLowerCase()
  if (!keyword) return visibleDetails.value

  return visibleDetails.value.filter((item) =>
    (item.title || "").toLowerCase().includes(keyword),
  )
})

const totalPages = computed(() =>
  Math.max(1, Math.ceil(filteredDetails.value.length / detailPageSize)),
)

const paginationItems = computed(() =>
  buildPaginationItems(currentPage.value, totalPages.value),
)

const pagedDetails = computed(() => {
  const start = (currentPage.value - 1) * detailPageSize
  return filteredDetails.value.slice(start, start + detailPageSize)
})

const hasFailedVideos = computed(() =>
  !["RUNNING", "STOP_REQUESTED"].includes(props.run.status) &&
  failedDetails.value.length > 0,
)

const currentListTitle = computed(() => {
  if (showIgnored.value) return "已忽略视频"
  if (showFailed.value) return "失败视频"
  if (showExisting.value) return "已存在视频"
  return "本次处理视频"
})

const existingToggleText = computed(() =>
  showExisting.value ? "查看本次处理视频" : `查看已存在视频 ${existingDetails.value.length}`,
)

const ignoredToggleText = computed(() =>
  showIgnored.value ? "查看本次处理视频" : `查看已忽略视频 ${ignoredDetails.value.length}`,
)

const failedToggleText = computed(() => {
  if (!hasFailedVideos.value) return "视频已全部完成"
  if (showFailed.value) return "查看本次处理视频"
  return `查看失败视频 ${failedDetails.value.length}`
})

const emptyDetailText = computed(() => {
  if (detailKeyword.value.trim()) return "没有匹配的视频名"
  if (showIgnored.value) return "本次没有已忽略视频"
  if (showFailed.value) return "本次没有失败视频"
  if (showExisting.value) return "本次范围内没有已存在视频"
  if (existingDetails.value.length > 0) return "本次没有需要新处理的视频，可查看已存在视频"
  return "暂无执行明细"
})

function artifactTarget(item) {
  if (item.docxPath) return { path: item.docxPath, label: "查看文档" }
  if (item.wavPath) return { path: item.wavPath, label: "查看音频" }
  if (item.mp4Path) return { path: item.mp4Path, label: "查看视频" }
  return null
}

function statusView(item) {
  return getVideoStatusView(item.status, props.run.status, item.errorStep, item.errorMessage)
}

function goToDetailPage(page) {
  currentPage.value = clampPage(page, totalPages.value)
}

function jumpToDetailPage() {
  if (detailPageJump.value === "") return
  goToDetailPage(detailPageJump.value)
  detailPageJump.value = ""
}

function toggleExistingDetails() {
  showExisting.value = !showExisting.value
  if (showExisting.value) {
    showFailed.value = false
    showIgnored.value = false
    cancelFailedSelectMode()
  }
}

function toggleFailedDetails() {
  showFailed.value = !showFailed.value
  if (showFailed.value) {
    showExisting.value = false
    showIgnored.value = false
  } else {
    cancelFailedSelectMode()
  }
}

function toggleIgnoredDetails() {
  showIgnored.value = !showIgnored.value
  if (showIgnored.value) {
    showExisting.value = false
    showFailed.value = false
    cancelFailedSelectMode()
  }
}

function enterFailedSelectMode() {
  failedSelectMode.value = true
  selectedFailedIds.value = []
}

function cancelFailedSelectMode() {
  failedSelectMode.value = false
  selectedFailedIds.value = []
}

function selectAllFailedVideos() {
  selectedFailedIds.value = filteredDetails.value.map((item) => item.id)
}

function toggleFailedSelection(id) {
  if (selectedFailedIds.value.includes(id)) {
    selectedFailedIds.value = selectedFailedIds.value.filter((item) => item !== id)
    return
  }
  selectedFailedIds.value = [...selectedFailedIds.value, id]
}

function ignoreSelectedFailedVideos() {
  if (selectedFailedIds.value.length === 0) return
  emit("ignore-videos", {
    runId: props.run.id,
    ids: selectedFailedIds.value,
  })
  cancelFailedSelectMode()
}

function rerunSelectedFailedVideos() {
  if (selectedFailedIds.value.length === 0) return
  emit("rerun-videos", {
    runId: props.run.id,
    ids: selectedFailedIds.value,
  })
  cancelFailedSelectMode()
}

watch([showExisting, showFailed, showIgnored, detailKeyword], () => {
  currentPage.value = 1
})

watch(totalPages, (pages) => {
  if (currentPage.value > pages) {
    currentPage.value = pages
  }
})

</script>
