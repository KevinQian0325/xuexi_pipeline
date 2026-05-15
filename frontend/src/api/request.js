const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ""

export async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  })

  if (!response.ok) {
    let message = `请求失败：${response.status}`
    const text = await response.text()
    try {
      const errorBody = text ? JSON.parse(text) : null
      message = errorBody.detail || errorBody.message || message
    } catch {
      if (text) message = text
    }
    throw new Error(message)
  }

  if (response.status === 204) return null
  return response.json()
}
