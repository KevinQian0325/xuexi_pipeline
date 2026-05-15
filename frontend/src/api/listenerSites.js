import { request } from "./request"

export function listListenerSites(keyword = "") {
  return request(`/api/listener-sites?keyword=${encodeURIComponent(keyword)}`)
}

export function createListenerSite(payload) {
  return request("/api/listener-sites", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export function updateListenerSiteRemark(id, remark) {
  return request(`/api/listener-sites/${id}/remark`, {
    method: "PATCH",
    body: JSON.stringify({ remark }),
  })
}

export function updateListenerSiteTimeRange(id, startDate, endDate) {
  return request(`/api/listener-sites/${id}/time-range`, {
    method: "PATCH",
    body: JSON.stringify({ startDate, endDate }),
  })
}

export function updateListenerSiteStatus(id, enabled) {
  return request(`/api/listener-sites/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ enabled }),
  })
}

export function deleteListenerSite(id) {
  return request(`/api/listener-sites/${id}`, {
    method: "DELETE",
  })
}
