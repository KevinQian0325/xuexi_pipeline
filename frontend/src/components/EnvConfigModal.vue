<template>
  <BaseModal
    title="系统配置"
    description="配置识别密钥和结果文件存储根目录"
    size="medium"
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

      <div class="config-divider"></div>

      <div class="config-section-title">
        <h4>存储地址配置</h4>
        <p>{{ storageDescription }}</p>
      </div>

      <label class="field-block">
        <span>结果文件存储根目录</span>
        <div class="path-input-row">
          <input
            v-model.trim="form.resultFilesDir"
            class="text-input"
            type="text"
            placeholder="请输入服务器本机上的存储根目录"
            :disabled="!canEditServerPaths"
          />
          <button
            class="secondary-button"
            type="button"
            :disabled="!canEditServerPaths"
            @click="chooseStoragePath"
          >
            选择
          </button>
        </div>
      </label>

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
import { computed, reactive, ref } from "vue"
import BaseModal from "./BaseModal.vue"

const emit = defineEmits(["close", "submit"])

const props = defineProps({
  initialValue: {
    type: Object,
    default: () => ({
      xuexiAppId: "",
      xuexiAccessToken: "",
      resultFilesDir: "",
    }),
  },
  canEditServerPaths: {
    type: Boolean,
    default: false,
  },
})

const form = reactive({
  xuexiAppId: props.initialValue.xuexiAppId ?? "",
  xuexiAccessToken: props.initialValue.xuexiAccessToken ?? "",
  resultFilesDir: props.initialValue.resultFilesDir ?? "",
})

const errorMessage = ref("")

const storageDescription = computed(() => {
  if (props.canEditServerPaths) {
    return "首次使用前必须设置。程序会自动在这个根目录下创建“结果文件”文件夹。"
  }
  return "此地址绑定服务器本机，远程访问时只能查看，不能修改。"
})

function submitForm() {
  if (!form.xuexiAppId || !form.xuexiAccessToken) {
    errorMessage.value = "请填写 XUEXI_APP_ID 和 XUEXI_ACCESS_TOKEN。"
    return
  }
  if (!form.resultFilesDir) {
    errorMessage.value = "请填写结果文件存储根目录。"
    return
  }

  emit("submit", {
    xuexiAppId: form.xuexiAppId,
    xuexiAccessToken: form.xuexiAccessToken,
    resultFilesDir: form.resultFilesDir,
  })
}

async function chooseStoragePath() {
  const path = window.prompt("请输入服务器本机上的存储根目录", form.resultFilesDir)
  if (path !== null) {
    form.resultFilesDir = path.trim()
  }
}
</script>
