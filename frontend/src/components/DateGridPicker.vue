<template>
  <div class="date-grid-picker">
    <div class="date-grid-toolbar">
      <div class="nav-group">
        <button class="nav-button" type="button" @click="changeYear(-1)">&lt;&lt;</button>
        <button class="nav-button" type="button" @click="changeMonth(-1)">‹</button>
      </div>
      <div class="month-label">{{ monthLabel }}</div>
      <div class="nav-group">
        <button class="nav-button" type="button" @click="changeMonth(1)">›</button>
        <button class="nav-button" type="button" @click="changeYear(1)">&gt;&gt;</button>
      </div>
    </div>

    <div class="weekday-row">
      <span v-for="weekday in weekdays" :key="weekday">{{ weekday }}</span>
    </div>

    <div class="grid-body">
      <button
        v-for="cell in calendarCells"
        :key="cell.key"
        class="date-cell"
        :class="{
          'is-muted': !cell.currentMonth,
          'is-selected': modelValue === cell.value,
          'is-today': today === cell.value,
        }"
        type="button"
        @click="$emit('update:modelValue', cell.value)"
      >
        {{ cell.day }}
      </button>
    </div>

    <button v-if="modelValue" class="text-action" type="button" @click="$emit('update:modelValue', null)">
      清空日期
    </button>
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue"

const props = defineProps({
  modelValue: { type: String, default: null },
})

defineEmits(["update:modelValue"])

const weekdays = ["一", "二", "三", "四", "五", "六", "日"]
const today = formatDate(new Date())
const visibleMonth = ref(getInitialVisibleMonth(props.modelValue))

watch(
  () => props.modelValue,
  (value) => {
    if (value) {
      visibleMonth.value = getInitialVisibleMonth(value)
    }
  },
)

const monthLabel = computed(() => {
  const date = new Date(visibleMonth.value.year, visibleMonth.value.month, 1)
  return date.toLocaleDateString("zh-CN", { year: "numeric", month: "long" })
})

const calendarCells = computed(() => {
  const { year, month } = visibleMonth.value
  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0)
  const startOffset = (firstDay.getDay() + 6) % 7
  const cells = []

  for (let index = 0; index < 42; index += 1) {
    const dayOffset = index - startOffset + 1
    const date = new Date(year, month, dayOffset)
    cells.push({
      key: `${year}-${month}-${index}`,
      value: formatDate(date),
      day: date.getDate(),
      currentMonth: date.getMonth() === month,
    })
  }

  if (cells.length > 35 && cells.slice(35).every((cell) => !cell.currentMonth)) {
    return cells.slice(0, 35)
  }

  return cells
})

function changeMonth(step) {
  const base = new Date(visibleMonth.value.year, visibleMonth.value.month + step, 1)
  visibleMonth.value = {
    year: base.getFullYear(),
    month: base.getMonth(),
  }
}

function changeYear(step) {
  visibleMonth.value = {
    year: visibleMonth.value.year + step,
    month: visibleMonth.value.month,
  }
}

function getInitialVisibleMonth(value) {
  if (value) {
    const [year, month] = value.split("-").map(Number)
    return { year, month: month - 1 }
  }

  const now = new Date()
  return { year: now.getFullYear(), month: now.getMonth() }
}

function formatDate(date) {
  const pad = (number) => String(number).padStart(2, "0")
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}
</script>
