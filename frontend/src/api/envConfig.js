let envConfig = {
  xuexiAppId: "",
  xuexiAccessToken: "",
}

const delay = (ms = 120) => new Promise((resolve) => setTimeout(resolve, ms))

export async function getEnvConfig() {
  await delay()
  return { ...envConfig }
}

export async function updateEnvConfig(payload) {
  await delay()
  envConfig = {
    xuexiAppId: payload.xuexiAppId,
    xuexiAccessToken: payload.xuexiAccessToken,
  }
  return { message: "密钥配置已保存" }
}
