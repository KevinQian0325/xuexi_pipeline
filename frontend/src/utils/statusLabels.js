export const VIDEO_STATUS_LABELS = {
  NEW: "待处理",
  NOT_VIDEO: "非视频内容",
  M3U8_DONE: "已解析视频地址",
  VIDEO_DONE: "已下载视频",
  AUDIO_DONE: "已提取音频",
  ASR_DONE: "已完成转写",
  PROCESSING: "处理中",
  DOCX_DONE: "已生成文档",
  EXISTING: "已存在",
  IGNORED: "已忽略",
  FAILED: "处理失败",
}

export const VIDEO_FAILURE_LABELS = {
  NEW: "处理失败：未开始处理",
  NOT_VIDEO: "处理失败：非视频内容",
  M3U8_DONE: "处理失败：视频下载失败",
  VIDEO_DONE: "处理失败：音频提取失败",
  AUDIO_DONE: "处理失败：转写失败",
  ASR_DONE: "处理失败：文档生成失败",
  PROCESSING: "处理失败：未完成",
  FAILED: "处理失败：运行异常",
}

export const VIDEO_FAILURE_STEP_LABELS = {
  M3U8_CAPTURE: "处理失败：视频地址解析失败",
  VIDEO_DOWNLOAD: "处理失败：视频下载失败",
  AUDIO_EXTRACT: "处理失败：音频提取失败",
  ASR_RECOGNIZE: "处理失败：转写失败",
  DOCX_GENERATE: "处理失败：文档生成失败",
}

export const ASR_ERROR_CODE_LABELS = {
  20000003: "静音音频",
  45000001: "请求参数无效",
  45000002: "空音频",
  45000151: "音频格式不正确",
  5500031: "服务器繁忙",
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

function getAsrFailureLabel(errorMessage = "") {
  const message = String(errorMessage)
  const exactCode = message.match(/\b(20000003|45000001|45000002|45000151|5500031)\b/)?.[1]
  if (exactCode) {
    return `处理失败：转写失败\n${ASR_ERROR_CODE_LABELS[exactCode]}`
  }

  if (/\b550\d+\b/.test(message)) {
    return "处理失败：转写失败\n服务内部处理错误"
  }

  return VIDEO_FAILURE_STEP_LABELS.ASR_RECOGNIZE
}

export function getVideoStatusView(status, runStatus, errorStep = "", errorMessage = "") {
  if (status === "EXISTING") {
    return {
      label: VIDEO_STATUS_LABELS.EXISTING,
      className: "is-success",
    }
  }

  if (status === "IGNORED") {
    return {
      label: VIDEO_STATUS_LABELS.IGNORED,
      className: "is-muted",
    }
  }

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

  if (status === "FAILED" && errorStep) {
    if (errorStep === "ASR_RECOGNIZE") {
      return {
        label: getAsrFailureLabel(errorMessage),
        className: "is-error",
      }
    }

    return {
      label: VIDEO_FAILURE_STEP_LABELS[errorStep] ?? VIDEO_FAILURE_LABELS.FAILED,
      className: "is-error",
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

export function formatRunProgress(status, successCount, totalCount) {
  if (status === "RUNNING" && Number(totalCount) === 0) {
    return "等待处理中"
  }

  if (status === "SUCCESS" && Number(totalCount) === 0) {
    return "无额外执行任务"
  }

  return `${formatRunStatus(status)} ${successCount}/${totalCount} 条`
}
