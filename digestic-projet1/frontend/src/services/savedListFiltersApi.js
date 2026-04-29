import api from './api'

/**
 * Client API pour GET/POST/DELETE /table-views/{viewKey}/saved-filters
 * (même forme que les filtres enregistrés pharmacies).
 * @param {string} viewKey - ex. 'pharmacies' | 'invoices' | 'delivery_notes'
 */
export function createSavedListFiltersClient(viewKey) {
  const base = `/table-views/${viewKey}/saved-filters`
  return {
    async list() {
      const { data } = await api.get(base)
      return Array.isArray(data) ? data : []
    },
    async create(body) {
      const { data } = await api.post(base, body)
      return data
    },
    async remove(id) {
      await api.delete(`${base}/${id}`)
    },
  }
}

/** @type {ReturnType<typeof createSavedListFiltersClient>} */
let _pharmacyClient
export function getPharmacySavedFiltersClient() {
  if (!_pharmacyClient) {
    _pharmacyClient = createSavedListFiltersClient('pharmacies')
  }
  return _pharmacyClient
}

/** @type {ReturnType<typeof createSavedListFiltersClient> | null} */
let _invoiceClient
export function getInvoiceSavedFiltersClient() {
  if (!_invoiceClient) {
    _invoiceClient = createSavedListFiltersClient('invoices')
  }
  return _invoiceClient
}

let _deliveryNotesClient
export function getDeliveryNotesSavedFiltersClient() {
  if (!_deliveryNotesClient) {
    _deliveryNotesClient = createSavedListFiltersClient('delivery_notes')
  }
  return _deliveryNotesClient
}
