<template>
  <BaseModal
    title="设定爬取时间范围"
    description="时间粒度按天保存。"
    size="large"
    @close="$emit('close')"
  >
    <div class="picker-grid">
      <div class="picker-panel">
        <div class="picker-title">
          <span>开始日期</span>
        </div>
        <DateGridPicker v-model="startDate" />
      </div>

      <div class="picker-panel">
        <div class="picker-title">
          <span>结束日期</span>
        </div>
        <DateGridPicker v-model="endDate" />
      </div>
    </div>

    <div v-if="!startDate" class="inline-warning">
      建议设定开始时间，避免爬取过早的视频。未设置时将从最早内容开始。
    </div>

    <div v-if="!endDate" class="inline-note">
      未设置结束时间时，将爬取到最新内容。
    </div>

    <div v-if="errorMessage" class="form-error">{{ errorMessage }}</div>

    <template #footer>
      <button class="secondary-button" type="button" @click="$emit('close')">取消</button>
      <button class="primary-button" type="button" @click="submit">保存</button>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref } from "vue"
import BaseModal from "./BaseModal.vue"
import DateGridPicker from "./DateGridPicker.vue"

const props = defineProps({
  initialStartDate: { type: String, default: null },
  initialEndDate: { type: String, default: null },
})

const emit = defineEmits(["close", "submit"])

const startDate = ref(props.initialStartDate)
const endDate = ref(props.initialEndDate)
const errorMessage = ref("")

function submit() {
  errorMessage.value = ""

  if (startDate.value && endDate.value && startDate.value > endDate.value) {
    errorMessage.value = "开始日期不能晚于结束日期。"
    return
  }

  if (!startDate.value) {
    const confirmed = window.confirm("建议设定开始时间，避免爬取过早的视频。未设置时将从最早内容开始。是否继续保存？")
    if (!confirmed) {
      return
    }
  }

  emit("submit", {
    startDate: startDate.value,
    endDate: endDate.value,
  })
}
</script>
