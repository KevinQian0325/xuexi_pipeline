import { request } from "./request"

export function getEnvConfig() {
  return request("/api/env-config")
}

export function updateEnvConfig(payload) {
  return request("/api/env-config", {
    method: "PUT",
    body: JSON.stringify(payload),
  })
}
