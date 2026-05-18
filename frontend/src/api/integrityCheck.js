import { request } from "./request"

export function checkFileIntegrity(siteIds) {
  return request("/api/integrity-check", {
    method: "POST",
    body: JSON.stringify({ siteIds }),
  })
}

export function repairFileIntegrity(siteIds) {
  return request("/api/integrity-check/repair", {
    method: "POST",
    body: JSON.stringify({ siteIds }),
  })
}
