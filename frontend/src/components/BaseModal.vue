<template>
  <div class="modal-backdrop" @click.self="$emit('close')">
    <div class="modal-card" :class="sizeClass">
      <div class="modal-header">
        <div>
          <h3>{{ title }}</h3>
          <p v-if="description">{{ description }}</p>
        </div>
        <button class="icon-button" type="button" @click="$emit('close')">×</button>
      </div>
      <div class="modal-body">
        <slot />
      </div>
      <div v-if="$slots.footer" class="modal-footer">
        <slot name="footer" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue"

const props = defineProps({
  title: { type: String, required: true },
  description: { type: String, default: "" },
  size: { type: String, default: "medium" },
})

defineEmits(["close"])

const sizeClass = computed(() => `modal-${props.size}`)
</script>
