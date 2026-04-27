import {
  PHARM_TABLE_ACTIONS_PX,
  PHARM_TABLE_PX_STORAGE_V,
} from '../constants/pharmacyTableMinWidths'

const STORAGE_KEY = 'digestic.pharmacies.tableColumnWidthsPx'

export function defaultEqualFractions(resizableOrder) {
  if (!resizableOrder?.length) {
    return {}
  }
  const n = resizableOrder.length
  return Object.fromEntries(resizableOrder.map((k) => [k, 1 / n]))
}

export function isValidLoadedPx(px, resizableOrder) {
  if (!px || typeof px !== 'object' || !resizableOrder?.length) {
    return false
  }
  for (const k of resizableOrder) {
    const num = Number(px[k])
    if (!Number.isFinite(num) || num < 32) {
      return false
    }
  }
  return true
}

export function loadColumnWidthsPx(resizableOrder) {
  if (!resizableOrder?.length) {
    return null
  }
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) {
      return null
    }
    const j = JSON.parse(raw)
    if (j.v !== PHARM_TABLE_PX_STORAGE_V || !j.px || !j.order) {
      return null
    }
    if (j.order !== resizableOrder.join(',')) {
      return null
    }
    if (!isValidLoadedPx(j.px, resizableOrder)) {
      return null
    }
    return { ...j.px }
  } catch {
    return null
  }
}

export function saveColumnWidthsPx(resizableOrder, px) {
  try {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        v: PHARM_TABLE_PX_STORAGE_V,
        order: resizableOrder.join(','),
        px,
      }),
    )
  } catch {
    /* ignore */
  }
}

function hamiltonToInt(exact, target) {
  if (exact.length === 0) {
    return []
  }
  const t = target !== undefined && target > 0 ? target : exact.reduce((a, b) => a + b, 0)
  const base = exact.map((x) => Math.floor(x))
  const fr = exact.map((x, i) => x - base[i])
  let rem = Math.round(t) - base.reduce((a, b) => a + b, 0)
  const byHigh = exact.map((_, i) => i).sort((a, b) => fr[b] - fr[a])
  for (let r = 0; r < rem; r++) {
    base[byHigh[r % byHigh.length]]++
  }
  if (rem < 0) {
    const byLow = exact.map((_, i) => i).sort((a, b) => fr[a] - fr[b])
    let deficit = -rem
    let i = 0
    while (deficit > 0 && i < 100) {
      const j = byLow[i % byLow.length]
      if (base[j] > 0) {
        base[j]--
        deficit--
      }
      i++
    }
  }
  return base
}

/**
 * @param {Record<string, number>} frac
 * @param {number} containerW
 * @param {Record<string, number>} minPx
 * @param {string[]} resizableOrder
 * @param {number} [tableActionsWidthPx=PHARM_TABLE_ACTIONS_PX] - colonne d’actions (ou PDF) à l’extérieur des largeurs resizables
 */
export function computeResizablePixelWidths(frac, containerW, minPx, resizableOrder, tableActionsWidthPx = PHARM_TABLE_ACTIONS_PX) {
  const ro = resizableOrder || []
  const W = Math.max(200, containerW)
  const A = tableActionsWidthPx
  const avail = W - A
  if (avail < 4 || ro.length === 0) {
    const colWidths = Object.fromEntries(ro.map((k) => [k, minPx[k] ?? 64]))
    const tableMinWidth = ro.reduce((a, k) => a + (minPx[k] ?? 64), 0) + A
    return {
      colWidths,
      actions: A,
      tableMinWidth,
      overflow: true,
    }
  }

  const s = ro.reduce((a, k) => a + (frac[k] ?? 0), 0) || 1
  const f = (k) => (frac[k] ?? 0) / s
  const exactRaw = ro.map((k) => f(k) * avail)
  const withMin = ro.map((k, i) => Math.max(minPx[k] ?? 64, exactRaw[i]))
  const S = withMin.reduce((a, b) => a + b, 0)

  if (S > avail + 0.5) {
    const rounded = withMin.map((x) => Math.round(x))
    const tsum = rounded.reduce((a, b) => a + b, 0) + A
    return {
      colWidths: Object.fromEntries(ro.map((k, i) => [k, rounded[i]])),
      actions: A,
      tableMinWidth: tsum,
      overflow: true,
    }
  }

  const add = avail - S
  const spread = withMin.map((v, i) => v + add * f(ro[i]))
  const intParts = hamiltonToInt(spread, avail)
  return {
    colWidths: Object.fromEntries(ro.map((k, i) => [k, intParts[i]])),
    actions: A,
    tableMinWidth: W,
    overflow: false,
  }
}
