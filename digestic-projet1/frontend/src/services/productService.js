import api from './api'

export const productService = {
  /**
   * @param {{ active_only?: boolean }} [params]
   */
  list: (params = {}) =>
    api.get('/products', { params }).then((r) => r.data),

  get: (id) => api.get(`/products/${id}`).then((r) => r.data),

  create: (data) => api.post('/products', data).then((r) => r.data),

  update: (id, data) => api.put(`/products/${id}`, data).then((r) => r.data),

  /** Désactivation logique côté API */
  delete: (id) => api.delete(`/products/${id}`).then((r) => r.data),
}
