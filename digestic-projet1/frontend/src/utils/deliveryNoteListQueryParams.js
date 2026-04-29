/**
 * Filtres UI liste bons de livraison (saved_list_filter_service + GET /delivery-notes).
 */
import { parseDepositFilterFromSearchParams } from './invoiceListQueryParams'

export const EMPTY_DELIVERY_NOTE_FILTERS = {
  pharmacyName: '',
  commercial: [],
  status: '',
  deliveryDate: '',
  depositId: '',
  includeArchived: false,
  sageReference: '',
  isDepositSale: '',
  emailSent: '',
}

const MULTI = new Set(['commercial'])

export function deliveryNoteFiltersFromPayload(raw) {
  const base = { ...EMPTY_DELIVERY_NOTE_FILTERS }
  if (!raw || typeof raw !== 'object') {
    return base
  }
  const src = { ...raw }
  if (Array.isArray(src.commercialIds) && !Array.isArray(src.commercial)) {
    src.commercial = src.commercialIds
  }
  if (
    (src.deliveryDate === undefined || src.deliveryDate === '') &&
    (src.deliveryDateFrom || src.deliveryDateTo)
  ) {
    const a = String(src.deliveryDateFrom || '').trim()
    const b = String(src.deliveryDateTo || '').trim()
    if (a && b && a === b) {
      src.deliveryDate = a
    } else if (a && !b) {
      src.deliveryDate = a
    } else if (!a && b) {
      src.deliveryDate = b
    } else if (a && b) {
      src.deliveryDate = a
    }
  }
  for (const key of Object.keys(EMPTY_DELIVERY_NOTE_FILTERS)) {
    if (src[key] === undefined) {
      continue
    }
    if (MULTI.has(key)) {
      const v = src[key]
      if (Array.isArray(v)) {
        base[key] = v.map((x) => String(x).trim()).filter(Boolean)
      } else if (v != null && String(v).trim()) {
        base[key] = [String(v).trim()]
      }
    } else if (key === 'includeArchived') {
      const v = src[key]
      if (v === true || v === false) {
        base[key] = v
      } else {
        const s = String(v || '').toLowerCase()
        base[key] = ['1', 'true', 'yes', 'oui', 'y'].includes(s)
      }
    } else if (src[key] == null) {
      base[key] = key === 'includeArchived' ? false : ''
    } else {
      base[key] = String(src[key]).trim()
    }
  }
  return base
}

export function getInitialDeliveryNoteFiltersState() {
  const base = { ...EMPTY_DELIVERY_NOTE_FILTERS }
  if (typeof window === 'undefined') {
    return base
  }
  const extra = parseDepositFilterFromSearchParams(new URLSearchParams(window.location.search))
  if (!extra) {
    return base
  }
  return { ...base, ...extra, includeArchived: true }
}

export function buildDeliveryNoteListQueryParams({
  page,
  rowsPerPage,
  orderBy,
  order,
  debouncedFilters: d,
}) {
  const params = {
    page: page + 1,
    page_size: rowsPerPage,
    sort: orderBy,
    order,
  }
  if (d.pharmacyName) {
    params.pharmacy_name = d.pharmacyName
  }
  if (Array.isArray(d.commercial) && d.commercial.length) {
    params.commercial_id = d.commercial.map((x) => String(x).trim()).filter(Boolean)
  }
  if (d.status) {
    params.status = d.status
  }
  if (d.deliveryDate && String(d.deliveryDate).trim()) {
    const day = String(d.deliveryDate).trim().slice(0, 10)
    params.delivery_date_from = day
    params.delivery_date_to = day
  }
  if (d.depositId) {
    params.deposit_id = d.depositId
  }
  if (d.includeArchived) {
    params.include_archived = true
  }
  if (d.sageReference) {
    params.sage_reference = d.sageReference
  }
  if (d.isDepositSale === 'yes') {
    params.is_deposit_sale = true
  } else if (d.isDepositSale === 'no') {
    params.is_deposit_sale = false
  }
  if (d.emailSent) {
    params.email_sent = d.emailSent
  }
  return params
}

export function hasDirtyDeliveryNoteFilters(f) {
  if (f.includeArchived) {
    return true
  }
  if (f.pharmacyName || f.status || f.deliveryDate || f.depositId) {
    return true
  }
  if (f.sageReference || f.isDepositSale || f.emailSent) {
    return true
  }
  if ((f.commercial && f.commercial.length)) {
    return true
  }
  return false
}
