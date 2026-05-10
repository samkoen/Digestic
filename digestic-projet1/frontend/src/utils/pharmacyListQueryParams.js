/**
 * Construit les query params de GET /pharmacies (noms d’attributs API).
 * Les filtres côté UI utilisent les clés de colonnes (ex. lastVisit, postalCodes).
 */
export const EMPTY_PHARMACY_FILTERS = {
  name: '',
  address: '',
  city: [],
  postalCodes: [],
  country: '',
  email: '',
  phone: '',
  pharmacistName: '',
  commercial: [],
  depot: [],
  lastVisit: '',
  nextVisit: '',
  status: '',
  paymentMode: [],
  rib: '',
  created: '',
}

const MULTI_FILTER_KEYS = new Set([
  'postalCodes',
  'commercial',
  'paymentMode',
  'city',
  'depot',
])

/** Reconstruit l’objet filtres UI à partir d’un payload API (filtres enregistrés). */
export function pharmacyFiltersFromPayload(raw) {
  const base = { ...EMPTY_PHARMACY_FILTERS }
  if (!raw || typeof raw !== 'object') {
    return base
  }
  for (const key of Object.keys(EMPTY_PHARMACY_FILTERS)) {
    if (raw[key] === undefined) {
      continue
    }
    if (MULTI_FILTER_KEYS.has(key)) {
      const v = raw[key]
      if (Array.isArray(v)) {
        base[key] = v.map((x) => String(x).trim()).filter(Boolean)
      } else if (v != null && String(v).trim()) {
        base[key] = [String(v).trim()]
      }
    } else if (raw[key] == null) {
      base[key] = ''
    } else {
      base[key] = String(raw[key])
    }
  }
  return base
}

export function buildPharmacyListQueryParams({
  page,
  rowsPerPage,
  orderBy,
  order,
  debouncedFilters: d,
  advancedFilterId,
}) {
  const params = {
    page: page + 1,
    page_size: rowsPerPage,
    sort: orderBy,
    order,
  }
  if (d.name) params.name = d.name
  if (d.address) params.address = d.address
  if (Array.isArray(d.city) && d.city.length) {
    const cities = d.city.map((x) => String(x).trim()).filter(Boolean)
    if (cities.length) {
      params.city = cities
    }
  }
  if (Array.isArray(d.postalCodes) && d.postalCodes.length) {
    const codes = d.postalCodes.map((x) => String(x).trim()).filter(Boolean)
    if (codes.length) {
      params.postal_code = codes
    }
  }
  if (d.country) params.country = d.country
  if (d.email) params.email = d.email
  if (d.phone) params.phone = d.phone
  if (d.pharmacistName) params.owner_name = d.pharmacistName
  if (Array.isArray(d.commercial) && d.commercial.length) {
    const ids = d.commercial.map((x) => String(x).trim()).filter(Boolean)
    if (ids.length) {
      params.commercial_id = ids
    }
  }
  if (Array.isArray(d.depot) && d.depot.length) {
    const wids = d.depot.map((x) => String(x).trim()).filter(Boolean)
    if (wids.length) {
      params.warehouse_id = wids
    }
  }
  if (d.lastVisit) params.last_visit = d.lastVisit
  if (d.nextVisit) params.next_visit = d.nextVisit
  if (d.status) params.pharmacy_status = d.status
  if (Array.isArray(d.paymentMode) && d.paymentMode.length) {
    const modes = d.paymentMode.map((x) => String(x).trim()).filter(Boolean)
    if (modes.length) {
      params.payment_mode = modes
    }
  }
  if (d.rib) params.rib = d.rib
  if (d.created) params.created = d.created
  const af = advancedFilterId != null ? String(advancedFilterId).trim() : ''
  if (af) {
    params.advanced_filter_id = af
  }
  return params
}
