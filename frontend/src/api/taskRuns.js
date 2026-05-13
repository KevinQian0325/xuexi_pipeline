import { taskRuns as seedData } from "../mock/taskRuns"
import { getEnvConfig } from "./envConfig"

let runs = structuredClone(seedData)

const delay = (ms = 120) => new Promise((resolve) => setTimeout(resolve, ms))

export async function listTaskRuns() {
  await delay()

  return {
    items: runs.map((item, index) => ({
      ...item,
      index: index + 1,
    })),
    total: runs.length,
  }
}

export async function rerunFailedTaskVideos(runId) {
  await delay(500)

  let updatedRun = null

  runs = runs.map((run) => {
    if (run.id !== runId) return run

    const now = nowString()
    const details = run.details.map((item) => {
      if (item.status === "DOCX_DONE") return item

      return {
        ...item,
        status: "DOCX_DONE",
        executedAt: now,
        docxPath: buildDocxPath(run, item),
      }
    })

    updatedRun = {
      ...run,
      status: "SUCCESS",
      successCount: details.length,
      totalCount: details.length,
      executedAt: now,
      details,
    }

    return updatedRun
  })

  return {
    item: updatedRun,
    message: "失败视频已重新运行",
  }
}

export async function startListenerSiteRun(sites) {
  await delay(700)

  const now = nowString()
  const envConfig = await getEnvConfig()
  const resultStorageRoot = envConfig.resultFilesDir || "结果文件夹"
  const nextId = runs.reduce((maxId, item) => Math.max(maxId, item.id), 0) + 1
  const newRuns = sites.map((site, index) => {
    const totalCount = 3
    const resultDir = buildResultDir(resultStorageRoot, site.remark)
    const details = buildRunDetails(site, totalCount, now, resultDir)

    return {
      id: nextId + index,
      remark: site.remark,
      pageUrl: site.pageUrl,
      resultDir,
      status: "SUCCESS",
      successCount: totalCount,
      totalCount,
      executedAt: now,
      duration: "00:00:02",
      startDate: site.startDate,
      endDate: site.endDate,
      details,
    }
  })

  runs = [...newRuns, ...runs]

  return {
    items: newRuns,
    message: "运行任务已创建",
  }
}

function buildDocxPath(run, item) {
  const safeTitle = String(item.title).replace(/[/:*?"<>|\\]/g, "_")
  return `${run.resultDir}/${safeTitle}/文本.docx`
}

function buildRunDetails(site, count, executedAt, resultDir) {
  return Array.from({ length: count }, (_, index) => {
    const itemNumber = index + 1
    const title = `${site.remark} 视频 ${itemNumber}`
    const itemId = `${site.id}-${Date.now()}-${itemNumber}`
    const detailUrl = `https://www.xuexi.cn/lgpage/detail/index.html?id=${itemId}&item_id=${itemId}`
    const run = { resultDir }

    return {
      id: itemId,
      title,
      detailUrl,
      publishTime: buildPublishTime(site, itemNumber),
      executedAt,
      status: "DOCX_DONE",
      docxPath: buildDocxPath(run, { title }),
    }
  })
}

function buildResultDir(resultStorageRoot, remark) {
  const normalizedRoot = String(resultStorageRoot).replace(/[\\/]+$/, "")
  return `${normalizedRoot}/结果文件/${remark}`
}

function buildPublishTime(site, itemNumber) {
  if (site.startDate) {
    return `${site.startDate} ${String(itemNumber - 1).padStart(2, "0")}:00:00`
  }
  if (site.endDate) {
    return `${site.endDate} ${String(itemNumber - 1).padStart(2, "0")}:00:00`
  }
  return "暂无"
}

function nowString() {
  const now = new Date()
  const pad = (value) => String(value).padStart(2, "0")
  return [
    now.getFullYear(),
    pad(now.getMonth() + 1),
    pad(now.getDate()),
  ].join("-") + ` ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`
}
