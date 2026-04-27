import api from './api'

export const deliveryNoteService = {
  getAll: async (params = {}) => {
    const response = await api.get('/delivery-notes', { params })
    return response.data
  },
  /** Émet la facture à partir du BL (VosFactures si configuré). */
  issueInvoice: async (noteId, data) => {
    const response = await api.post(`/delivery-notes/${noteId}/facturer`, data)
    return response.data
  },
  /** @deprecated utiliser issueInvoice */
  convertToInvoice: async (noteId, data) => {
    const response = await api.post(`/delivery-notes/${noteId}/facturer`, data)
    return response.data
  },
}
