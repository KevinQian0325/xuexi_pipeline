const LOCAL_SERVER_HOSTS = new Set(["localhost", "127.0.0.1", "::1", "[::1]"])

export function isServerHostAccess() {
  if (typeof window === "undefined") return false

  const { protocol, hostname } = window.location
  if (protocol === "file:") return true

  return LOCAL_SERVER_HOSTS.has(hostname)
}
