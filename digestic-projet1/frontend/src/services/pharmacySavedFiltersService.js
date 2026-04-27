import { getPharmacySavedFiltersClient } from './savedListFiltersApi'

/**
 * @returns {Promise<Array<{ id: string, name: string, payload: object, updatedAt?: string }>>}
 */
export async function fetchPharmacySavedFilters() {
  return getPharmacySavedFiltersClient().list()
}

/**
 * @param {{ name: string, filters: object, orderBy: string, order: string }} body
 */
export async function createPharmacySavedFilter(body) {
  return getPharmacySavedFiltersClient().create(body)
}

export async function deletePharmacySavedFilter(id) {
  return getPharmacySavedFiltersClient().remove(id)
}
