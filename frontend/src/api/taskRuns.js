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
