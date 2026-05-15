import { request } from "./request"

export function openServerPath(path) {
  return request("/api/open-path", {
    method: "POST",
    body: JSON.stringify({ path }),
  })
}
