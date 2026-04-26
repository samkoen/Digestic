import api from './api'

const DEFAULT_LIST_PARAMS = { sort: 'name', order: 'asc' }

/**
 * @param {Record<string, unknown>} params — page, page_size, sort, order, filtres (name, address, …)
 * @returns {Promise<{ items: any[], total: number, page: number, page_size: number }>}
 */
function appendRepeatedQuery(sp, key, val) {
  if (Array.isArray(val)) {
    for (const p of val) {
      const t = String(p).trim()
      if (t) {
        sp.append(key, t)
      }
    }
  } else if (val !== undefined && val !== null && String(val).trim() !== '') {
    sp.append(key, String(val).trim())
  }
}

export const fetchPharmacyDistinctCities = async () => {
  const { data } = await api.get('/pharmacies/distinct-cities')
  return Array.isArray(data) ? data : []
}

export const fetchPharmaciesPage = async (params = {}) => {
  const merged = { ...DEFAULT_LIST_PARAMS, ...params }
  const {
    postal_code: postalCodeParam,
    commercial_id: commercialIdParam,
    payment_mode: paymentModeParam,
    city: cityParam,
    warehouse_id: warehouseIdParam,
    ...rest
  } = merged
  const sp = new URLSearchParams()
  for (const [k, v] of Object.entries(rest)) {
    if (v === undefined || v === null || v === '') {
      continue
    }
    sp.append(k, String(v))
  }
  appendRepeatedQuery(sp, 'postal_code', postalCodeParam)
  appendRepeatedQuery(sp, 'commercial_id', commercialIdParam)
  appendRepeatedQuery(sp, 'payment_mode', paymentModeParam)
  appendRepeatedQuery(sp, 'city', cityParam)
  appendRepeatedQuery(sp, 'warehouse_id', warehouseIdParam)
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
