/**
 * Filtres UI liste factures (alignés `saved_list_filter_service` + query GET /invoices).
 */
export const EMPTY_INVOICE_FILTERS = {
  invoiceNumber: '',
  pharmacyName: '',
  pharmacyId: '',
  depositId: '',
  status: '',
  overdueOnly: false,
  overdueMinDays: 30,
}

/**
 * Lit `pharmacy_id` / `pharmacy_name` depuis l’URL (ex. lien depuis la fiche pharmacie).
 * @param {URLSearchParams} sp
 * @returns {{ pharmacyId: string, pharmacyName: string } | null}
 */
export function parsePharmacyFilterFromSearchParams(sp) {
  if (!sp) {
    return null
  }
  const pid = (sp.get('pharmacy_id') || sp.get('pharmacyId') || '').trim()
  if (!pid) {
    return null
  }
  let name = (sp.get('pharmacy_name') || sp.get('pharmacyName') || '').trim()
  if (name) {
    try {
      name = decodeURIComponent(name)
    } catch {
      // chaîne déjà en clair
    }
  }
  return { pharmacyId: pid, pharmacyName: name }
}

/**
 * @param {URLSearchParams} sp
 * @returns {{ depositId: string } | null}
 */
export function parseDepositFilterFromSearchParams(sp) {
  if (!sp) {
    return null
  }
  const did = (sp.get('deposit_id') || sp.get('depositId') || '').trim()
  if (!did) {
    return null
  }
  return { depositId: did }
}

/**
 * @param {URLSearchParams} sp
 * @returns {{ invoiceNumber: string } | null}
 */
export function parseInvoiceNumberFilterFromSearchParams(sp) {
  if (!sp) {
    return null
  }
  const n = (sp.get('invoice_number') || sp.get('invoiceNumber') || '').trim()
  if (!n) {
    return null
  }
  return { invoiceNumber: n }
}

/** État initial filtres (window) pour premier GET aligné sur l’URL. */
export function getInitialInvoiceFiltersState() {
  const base = { ...EMPTY_INVOICE_FILTERS, overdueOnly: false }
  if (typeof window === 'undefined') {
    return base
  }
  const sp = new URLSearchParams(window.location.search)
  const extraP = parsePharmacyFilterFromSearchParams(sp)
  const extraD = parseDepositFilterFromSearchParams(sp)
  const extraN = parseInvoiceNumberFilterFromSearchParams(sp)
  if (!extraP && !extraD && !extraN) {
    return base
  }
  return { ...base, ...(extraP || {}), ...(extraD || {}), ...(extraN || {}) }
}

export function invoiceFiltersFromPayload(raw) {
  const base = { ...EMPTY_INVOICE_FILTERS }
  if (!raw || typeof raw !== 'object') {
    return base
  }
  for (const k of Object.keys(EMPTY_INVOICE_FILTERS)) {
    if (raw[k] === undefined) {
      continue
    }
    if (k === 'overdueOnly') {
      const v = raw[k]
      if (v === true || v === false) {
        base[k] = v
      } else {
        const s = String(v || '').toLowerCase()
        base[k] = ['1', 'true', 'yes', 'oui', 'y'].includes(s)
      }
    } else if (k === 'overdueMinDays') {
      const n = parseInt(String(raw[k]), 10)
      base[k] = Number.isFinite(n) ? Math.max(0, Math.min(n, 3650)) : 30
    } else {
      base[k] = raw[k] == null ? (k === 'status' ? '' : '') : String(raw[k]).trim()
    }
  }
  return base
}

export function buildInvoiceListQueryParams({
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
  if (d.invoiceNumber) {
    params.invoice_number = d.invoiceNumber
  }
  if (d.pharmacyName) {
    params.pharmacy_name = d.pharmacyName
  }
  if (d.pharmacyId) {
    params.pharmacy_id = d.pharmacyId
  }
  if (d.depositId) {
    params.deposit_id = d.depositId
  }
  if (d.status) {
    params.status = d.status
  }
  if (d.overdueOnly) {
    params.overdue_only = true
    params.overdue_min_days = d.overdueMinDays != null ? d.overdueMinDays : 30
  }
  return params
}
