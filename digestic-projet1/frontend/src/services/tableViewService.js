import api from './api'

/**
 * @returns {Promise<{ viewKey: string, definition: Array, visibleColumnKeys: string[] }>}
 */
export async function fetchPharmacyTableView() {
  const { data } = await api.get('/table-views/pharmacies')
  return data
}

/**
 * @param {string[]} visibleColumnKeys
 * @returns {Promise<{ viewKey: string, visibleColumnKeys: string[] }>}
 */
export async function savePharmacyTableView(visibleColumnKeys) {
  const { data } = await api.put('/table-views/pharmacies', {
    visibleColumnKeys,
  })
  return data
}
