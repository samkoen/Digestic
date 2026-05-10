import api from './api'

const base = '/pharmacy-advanced-filters'

export async function listPharmacyAdvancedFilters() {
  const { data } = await api.get(base)
  return Array.isArray(data) ? data : []
}

export async function getPharmacyAdvancedFilter(id) {
  const { data } = await api.get(`${base}/${id}`)
  return data
}

export async function createPharmacyAdvancedFilter(body) {
  const { data } = await api.post(base, body)
  return data
}

export async function updatePharmacyAdvancedFilter(id, body) {
  const { data } = await api.put(`${base}/${id}`, body)
  return data
}

export async function deletePharmacyAdvancedFilter(id) {
  await api.delete(`${base}/${id}`)
}
