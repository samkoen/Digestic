import api from './api'

/**
 * @returns {Promise<Array<{ id: string, name: string, payload: object, updatedAt?: string }>>}
 */
export async function fetchPharmacySavedFilters() {
  const { data } = await api.get('/table-views/pharmacies/saved-filters')
  return Array.isArray(data) ? data : []
}

/**
 * @param {{ name: string, filters: object, orderBy: string, order: string }} body
 */
export async function createPharmacySavedFilter(body) {
  const { data } = await api.post('/table-views/pharmacies/saved-filters', body)
  return data
}

export async function deletePharmacySavedFilter(id) {
  await api.delete(`/table-views/pharmacies/saved-filters/${id}`)
}
