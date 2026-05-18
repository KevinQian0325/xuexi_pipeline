export function buildPaginationItems(currentPage, totalPages) {
  const total = Math.max(1, Number(totalPages) || 1)
  const current = Math.min(Math.max(1, Number(currentPage) || 1), total)

  if (total <= 7) {
    return Array.from({ length: total }, (_, index) => index + 1)
  }

  if (current <= 4) {
    return [1, 2, 3, 4, 5, "end-ellipsis", total]
  }

  if (current >= total - 3) {
    return [1, "start-ellipsis", total - 4, total - 3, total - 2, total - 1, total]
  }

  return [1, "start-ellipsis", current - 1, current, current + 1, "end-ellipsis", total]
}

export function clampPage(page, totalPages) {
  const total = Math.max(1, Number(totalPages) || 1)
  const nextPage = Number(page)
  if (!Number.isFinite(nextPage)) return 1
  return Math.min(Math.max(1, Math.trunc(nextPage)), total)
}
