export const VIDEO_STATUS_LABELS = {
  NEW: "待处理",
  NOT_VIDEO: "非视频内容",
  M3U8_DONE: "已解析视频地址",
  VIDEO_DONE: "已下载视频",
  AUDIO_DONE: "已提取音频",
  ASR_DONE: "已完成转写",
  DOCX_DONE: "已生成文档",
  FAILED: "处理失败",
}

export const VIDEO_FAILURE_LABELS = {
  NEW: "处理失败：未开始处理",
  NOT_VIDEO: "处理失败：非视频内容",
  M3U8_DONE: "处理失败：视频下载失败",
  VIDEO_DONE: "处理失败：音频提取失败",
  AUDIO_DONE: "处理失败：转写失败",
  ASR_DONE: "处理失败：文档生成失败",
  FAILED: "处理失败：运行异常",
}

export const RUN_STATUS_LABELS = {
  RUNNING: "执行中",
  SUCCESS: "全部完成",
  PARTIAL_FAILED: "部分失败",
  FAILED: "执行失败",
}

export function formatVideoStatus(status) {
  return VIDEO_STATUS_LABELS[status] ?? status
}

export function formatVideoCustomerStatus(status, runStatus) {
  return getVideoStatusView(status, runStatus).label
}

export function getVideoStatusView(status, runStatus) {
  if (status === "DOCX_DONE") {
    return {
      label: VIDEO_STATUS_LABELS.DOCX_DONE,
      className: "is-success",
    }
  }

  if (runStatus === "RUNNING" && status !== "FAILED") {
    return {
      label: formatVideoStatus(status),
      className: status === "NEW" ? "is-muted" : "is-progress",
    }
  }

  return {
    label: VIDEO_FAILURE_LABELS[status] ?? `处理失败：${status}`,
    className: "is-error",
  }
}

export function formatRunStatus(status) {
  return RUN_STATUS_LABELS[status] ?? status
}
