import api from './api'

export const depotService = {
  list: () => api.get('/depots').then((r) => r.data),

  get: (id) => api.get(`/depots/${id}`).then((r) => r.data),

  create: (data) => api.post('/depots', data).then((r) => r.data),

  update: (id, data) => api.put(`/depots/${id}`, data).then((r) => r.data),

  addStock: (id, quantity) =>
    api.post(`/depots/${id}/add-stock`, { quantity }).then((r) => r.data),

  /**
   * @param {{ from_warehouse_id: string, to_warehouse_id: string, quantity: number }} data
   */
  transfer: (data) => api.post('/depots/transfer', data).then((r) => r.data),

  listTransfers: (limit = 100) =>
    api.get('/depots/transfers', { params: { limit } }).then((r) => r.data),
}
