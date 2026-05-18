import { request } from "./request"

export function listTaskRuns() {
  return request("/api/task-runs")
}

export function deleteTaskRuns(ids) {
  return request("/api/task-runs/delete", {
    method: "POST",
    body: JSON.stringify({ ids }),
  })
}

export function clearTaskRuns() {
  return request("/api/task-runs", {
    method: "DELETE",
  })
}

export function startListenerSiteRun(sites) {
  return request("/api/task-runs/start", {
    method: "POST",
    body: JSON.stringify({ sites }),
  })
}

export function rerunFailedTaskVideos(runId) {
  return request(`/api/task-runs/${runId}/rerun-failed`, {
    method: "POST",
  })
}

export function rerunTaskRunVideos(runId, ids) {
  return request(`/api/task-runs/${runId}/rerun-videos`, {
    method: "POST",
    body: JSON.stringify({ ids }),
  })
}

export function ignoreTaskRunVideos(runId, ids, reason = "用户确认忽略") {
  return request(`/api/task-runs/${runId}/ignore-videos`, {
    method: "POST",
    body: JSON.stringify({ ids, reason }),
  })
}
