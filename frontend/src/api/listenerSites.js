import { listenerSites as seedData } from "../mock/listenerSites"

let sites = structuredClone(seedData)

const delay = (ms = 120) => new Promise((resolve) => setTimeout(resolve, ms))

export async function listListenerSites(keyword = "") {
  await delay()

  const normalizedKeyword = keyword.trim().toLowerCase()
  const items = sites
    .filter((item) => {
      if (!normalizedKeyword) return true
      return (
        item.remark.toLowerCase().includes(normalizedKeyword) ||
        item.pageUrl.toLowerCase().includes(normalizedKeyword)
      )
    })
    .map((item, index) => ({
      ...item,
      index: index + 1,
    }))

  return {
    items,
    total: items.length,
  }
}

export async function createListenerSite(payload) {
  await delay()

  const nextId = sites.reduce((maxId, item) => Math.max(maxId, item.id), 0) + 1
  sites.unshift({
    id: nextId,
    remark: payload.remark,
    pageUrl: payload.pageUrl,
    enabled: true,
    startDate: payload.startDate,
    endDate: payload.endDate,
    updatedAt: nowString(),
  })

  return { id: nextId, message: "创建成功" }
}

export async function updateListenerSiteRemark(id, remark) {
  await delay()
  sites = sites.map((item) =>
    item.id === id ? { ...item, remark, updatedAt: nowString() } : item,
  )
  return { message: "备注修改成功" }
}

export async function updateListenerSiteTimeRange(id, startDate, endDate) {
  await delay()
  sites = sites.map((item) =>
    item.id === id
      ? { ...item, startDate, endDate, updatedAt: nowString() }
      : item,
  )
  return { message: "时间范围更新成功" }
}

export async function updateListenerSiteStatus(id, enabled) {
  await delay()
  sites = sites.map((item) =>
    item.id === id ? { ...item, enabled, updatedAt: nowString() } : item,
  )
  return { message: "状态更新成功" }
}

export async function deleteListenerSite(id) {
  await delay()
  sites = sites.filter((item) => item.id !== id)
  return { message: "删除成功" }
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
