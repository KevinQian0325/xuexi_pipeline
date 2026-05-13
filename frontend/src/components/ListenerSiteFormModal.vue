<template>
  <BaseModal
    :title="mode === 'create' ? '新增监听网页' : '修改备注'"
    :description="mode === 'create' ? '创建一个新的网页监听配置。' : '修改后，结果文件一级目录会同步使用新备注。'"
    :size="mode === 'create' ? 'large' : 'small'"
    @close="$emit('close')"
  >
    <form class="form-layout" @submit.prevent="submit">
      <template v-if="mode === 'create'">
        <label class="field-block">
          <span>备注 *</span>
          <input v-model.trim="form.remark" class="text-input" type="text" placeholder="请输入备注，例如：世界眼中的习近平" />
        </label>

        <label class="field-block">
          <span>网页地址 *</span>
          <input v-model.trim="form.pageUrl" class="text-input" type="url" placeholder="请输入需要监听的网页地址" />
        </label>

        <section class="range-section">
          <div class="section-heading">
            <div>
              <h4>爬取时间范围（按天）</h4>
              <p>开始日期不填时，将从该网页最早内容开始爬取；结束日期不填时，将爬取到最新内容。</p>
            </div>
          </div>

          <div class="picker-grid">
            <div class="picker-panel">
              <div class="picker-title">
                <span>开始日期</span>
              </div>
              <DateGridPicker v-model="form.startDate" />
            </div>

            <div class="picker-panel">
              <div class="picker-title">
                <span>结束日期</span>
              </div>
              <DateGridPicker v-model="form.endDate" />
            </div>
          </div>

          <div v-if="showStartReminder" class="inline-warning">
            建议设定开始时间，避免爬取过早的视频。未设置时将从最早内容开始。
          </div>

          <div v-if="!form.endDate" class="inline-note">
            未设置结束时间时，将爬取到最新内容。
          </div>
        </section>
      </template>

      <template v-else>
        <label class="field-block">
          <span>备注 *</span>
          <input v-model.trim="form.remark" class="text-input" type="text" placeholder="请输入新的备注" />
        </label>
      </template>

      <div v-if="errorMessage" class="form-error">{{ errorMessage }}</div>
    </form>

    <template #footer>
      <button class="secondary-button" type="button" @click="$emit('close')">取消</button>
      <button class="primary-button" type="button" @click="submit">保存</button>
    </template>
  </BaseModal>
</template>

<script setup>
import { computed, reactive, ref } from "vue"
import BaseModal from "./BaseModal.vue"
import DateGridPicker from "./DateGridPicker.vue"

const props = defineProps({
  mode: { type: String, required: true },
  initialValue: { type: Object, default: () => ({}) },
})

const emit = defineEmits(["close", "submit", "confirm-empty-start"])

const form = reactive({
  remark: props.initialValue.remark ?? "",
  pageUrl: props.initialValue.pageUrl ?? "",
  startDate: props.initialValue.startDate ?? null,
  endDate: props.initialValue.endDate ?? null,
})

const errorMessage = ref("")

const showStartReminder = computed(() => props.mode === "create" && !form.startDate)

function submit() {
  errorMessage.value = ""

  if (!form.remark) {
    errorMessage.value = "请填写备注。"
    return
  }

  if (props.mode === "create" && !form.pageUrl) {
    errorMessage.value = "请填写网页地址。"
    return
  }

  if (form.startDate && form.endDate && form.startDate > form.endDate) {
    errorMessage.value = "开始日期不能晚于结束日期。"
    return
  }

  if (props.mode === "create" && !form.startDate) {
    const confirmed = window.confirm("建议设定开始时间，避免爬取过早的视频。未设置时将从最早内容开始。是否继续保存？")
    if (!confirmed) {
      return
    }
  }

  emit("submit", {
    remark: form.remark,
    pageUrl: form.pageUrl,
    startDate: form.startDate,
    endDate: form.endDate,
  })
}
</script>
