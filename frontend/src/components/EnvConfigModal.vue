<template>
  <BaseModal
    title="密钥配置"
    description="用于音频转文字的大模型识别参数"
    size="small"
    @close="$emit('close')"
  >
    <form class="form-layout" @submit.prevent="submitForm">
      <label class="field-block">
        <span>XUEXI_APP_ID</span>
        <input
          v-model.trim="form.xuexiAppId"
          class="text-input"
          type="text"
          placeholder="请输入火山引擎 App ID"
        />
      </label>

      <label class="field-block">
        <span>XUEXI_ACCESS_TOKEN</span>
        <input
          v-model.trim="form.xuexiAccessToken"
          class="text-input"
          type="password"
          placeholder="请输入 Access Token"
        />
      </label>

      <a
        class="guide-link"
        href="https://console.volcengine.com/speech/service/10012"
        target="_blank"
        rel="noreferrer"
      >
        火山引擎录音文件识别大模型-极速版
      </a>

      <p v-if="errorMessage" class="form-error">{{ errorMessage }}</p>
    </form>

    <template #footer>
      <button class="secondary-button" type="button" @click="$emit('close')">
        取消
      </button>
      <button class="primary-button" type="button" @click="submitForm">
        保存
      </button>
    </template>
  </BaseModal>
</template>

<script setup>
import { reactive, ref } from "vue"
import BaseModal from "./BaseModal.vue"

const emit = defineEmits(["close", "submit"])

const props = defineProps({
  initialValue: {
    type: Object,
    default: () => ({
      xuexiAppId: "",
      xuexiAccessToken: "",
    }),
  },
})

const form = reactive({
  xuexiAppId: props.initialValue.xuexiAppId ?? "",
  xuexiAccessToken: props.initialValue.xuexiAccessToken ?? "",
})

const errorMessage = ref("")

function submitForm() {
  if (!form.xuexiAppId || !form.xuexiAccessToken) {
    errorMessage.value = "请填写 XUEXI_APP_ID 和 XUEXI_ACCESS_TOKEN。"
    return
  }

  emit("submit", {
    xuexiAppId: form.xuexiAppId,
    xuexiAccessToken: form.xuexiAccessToken,
  })
}
</script>
