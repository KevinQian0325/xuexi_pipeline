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
        <strong>{{ formatRunStatus(run.status) }} {{ run.successCount }}/{{ run.totalCount }} 条</strong>
      </div>
    </div>

    <div class="detail-actions">
      <button
        class="retry-button"
        type="button"
        :disabled="!hasFailedVideos || retrying"
        @click="$emit('rerun-failed', run.id)"
      >
        {{ retryButtonText }}
      </button>
    </div>

    <div class="table-wrapper detail-table-wrapper">
      <table class="site-table detail-table">
        <thead>
          <tr>
            <th>视频名</th>
            <th>视频网站</th>
            <th>视频发布时间</th>
            <th>执行时间</th>
            <th>状态</th>
            <th>文档地址</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in run.details" :key="item.id">
            <td>
              <strong class="video-title">{{ item.title }}</strong>
            </td>
            <td>
              <a class="url-link" :href="item.detailUrl" target="_blank" rel="noreferrer">
                {{ item.detailUrl }}
              </a>
            </td>
            <td>{{ item.publishTime || "暂无" }}</td>
            <td>{{ item.executedAt }}</td>
            <td>
              <span class="status-tag" :class="statusView(item.status, run.status).className">
                {{ statusView(item.status, run.status).label }}
              </span>
            </td>
            <td>
              <a
                v-if="canOpenServerPaths && item.docxPath"
                class="view-button"
                :href="toHref(item.docxPath)"
                target="_blank"
                rel="noreferrer"
              >
                查看
              </a>
              <span
                v-else-if="item.docxPath"
                class="server-machine-text"
                :title="item.docxPath"
              >
                非服务器机器
              </span>
              <span v-else class="muted-text">暂无</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </BaseModal>
</template>

<script setup>
import { computed } from "vue"
import BaseModal from "./BaseModal.vue"
import { formatRunStatus, getVideoStatusView } from "../utils/statusLabels"

defineEmits(["close", "rerun-failed"])

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

const hasFailedVideos = computed(() =>
  props.run.status !== "RUNNING" &&
  props.run.details.some((item) => item.status !== "DOCX_DONE"),
)

const retryButtonText = computed(() => {
  if (props.retrying) return "正在重新运行..."
  if (!hasFailedVideos.value) return "视频已全部完成"
  return "重新运行失败视频"
})

function statusView(status, runStatus) {
  return getVideoStatusView(status, runStatus)
}

function toHref(path) {
  if (/^https?:\/\//i.test(path)) return path
  return `file://${path}`
}
</script>
