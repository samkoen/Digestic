import api from './api'

export const deliveryNoteService = {
  getAll: async (params = {}) => {
    const response = await api.get('/delivery-notes', { params })
    return response.data
  },
  convertToInvoice: async (noteId, data) => {
    const response = await api.post(`/delivery-notes/${noteId}/convert`, data)
    return response.data
  },
}

