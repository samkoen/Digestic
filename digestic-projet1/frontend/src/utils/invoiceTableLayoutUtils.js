import {
  INVOICE_TABLE_ACTIONS_PX,
  INVOICE_COLUMN_MIN_PX,
} from '../constants/invoiceTableMinWidths'
import { PHARM_TABLE_PX_STORAGE_V } from '../constants/pharmacyTableMinWidths'
import {
  computeResizablePixelWidths,
  defaultEqualFractions,
  isValidLoadedPx,
} from './pharmacyTableLayoutUtils'

const STORAGE_KEY = 'digestic.invoices.tableColumnWidthsPx'

export function loadInvoiceColumnWidths(resizableOrder) {
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

export function saveInvoiceColumnWidths(resizableOrder, px) {
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

export {
  computeResizablePixelWidths,
  defaultEqualFractions,
  INVOICE_COLUMN_MIN_PX,
  INVOICE_TABLE_ACTIONS_PX,
}
