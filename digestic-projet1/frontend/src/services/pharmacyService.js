import api from './api'
import { buildSearchParamsForPagedList } from '../utils/httpQueryParams'

const DEFAULT_LIST_PARAMS = { sort: 'name', order: 'asc' }

/**
 * @param {Record<string, unknown>} params — page, page_size, sort, order, filtres (name, address, …)
 * @returns {Promise<{ items: any[], total: number, page: number, page_size: number }>}
 */
export const fetchPharmacyDistinctCities = async () => {
  const { data } = await api.get('/pharmacies/distinct-cities')
  return Array.isArray(data) ? data : []
}

export const fetchPharmaciesPage = async (params = {}) => {
  const merged = { ...DEFAULT_LIST_PARAMS, ...params }
  const sp = buildSearchParamsForPagedList({
    merged,
    repeatedParamKeys: [
      'postal_code',
      'commercial_id',
      'payment_mode',
      'city',
      'warehouse_id',
    ],
  })
  const response = await api.get('/pharmacies', { params: sp })
  return response.data
}

/**
 * Toutes les pharmacies (boucle côté client si besoin) — pour select / planning.
 */
export const pharmacyService = {
  /**
   * Une page (tri + filtres côté serveur).
   */
  getList: fetchPharmaciesPage,

  /**
   * Liste complète, par pages de 500 (pour écrans qui ont encore besoin de tout charger).
   */
  getAll: async (extra = {}) => {
    const all = []
    let page = 1
    const page_size = 500
    for (;;) {
      const data = await fetchPharmaciesPage({ page, page_size, ...extra })
      const chunk = data.items || []
      all.push(...chunk)
      if (all.length >= (data.total || 0) || chunk.length < page_size) {
        break
      }
      page += 1
      if (page > 200) {
        break
      }
    }
    return all
  },

  getById: async (id) => {
    const response = await api.get(`/pharmacies/${id}`)
    return response.data
  },

  create: async (pharmacyData) => {
    const response = await api.post('/pharmacies', pharmacyData)
    return response.data
  },

  update: async (id, pharmacyData) => {
    const response = await api.put(`/pharmacies/${id}`, pharmacyData)
    return response.data
  },

  delete: async (id) => {
    const response = await api.delete(`/pharmacies/${id}`)
    return response.data
  },

  getComments: async (pharmacyId) => {
    const response = await api.get(`/pharmacies/${pharmacyId}/comments`)
    return response.data
  },

  addComment: async (pharmacyId, text) => {
    const response = await api.post(`/pharmacies/${pharmacyId}/comments`, { text })
    return response.data
  },

  deleteComment: async (pharmacyId, commentId) => {
    const response = await api.delete(
      `/pharmacies/${pharmacyId}/comments/${commentId}`,
    )
    return response.data
  },
}
