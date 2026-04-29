import api from './api'

/**
 * @param {string} viewKey - ex. 'pharmacies' | 'invoices' | 'delivery_notes'
 * @returns {{ fetch: () => Promise, save: (visibleColumnKeys: string[]) => Promise }}
 */
export function createTableViewClient(viewKey) {
  const base = `/table-views/${viewKey}`
  return {
    async fetch() {
      const { data } = await api.get(base)
      return data
    },
    async save(visibleColumnKeys) {
      const { data } = await api.put(base, { visibleColumnKeys })
      return data
    },
  }
}

const _pharmacy = createTableViewClient('pharmacies')
const _invoice = createTableViewClient('invoices')
const _deliveryNotes = createTableViewClient('delivery_notes')

/**
 * @returns {Promise<{ viewKey: string, definition: Array, visibleColumnKeys: string[] }>}
 */
export async function fetchPharmacyTableView() {
  return _pharmacy.fetch()
}

/**
 * @param {string[]} visibleColumnKeys
 */
export async function savePharmacyTableView(visibleColumnKeys) {
  return _pharmacy.save(visibleColumnKeys)
}

export async function fetchInvoiceTableView() {
  return _invoice.fetch()
}

export async function saveInvoiceTableView(visibleColumnKeys) {
  return _invoice.save(visibleColumnKeys)
}

export async function fetchDeliveryNotesTableView() {
  return _deliveryNotes.fetch()
}

export async function saveDeliveryNotesTableView(visibleColumnKeys) {
  return _deliveryNotes.save(visibleColumnKeys)
}
