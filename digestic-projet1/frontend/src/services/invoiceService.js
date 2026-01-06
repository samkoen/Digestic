import api from './api'

export const invoiceService = {
  getAll: async (filters = {}) => {
    const response = await api.get('/invoices', { params: filters })
    return response.data
  },

  getById: async (id) => {
    const response = await api.get(`/invoices/${id}`)
    return response.data
  },

  create: async (invoiceData) => {
    const response = await api.post('/invoices', invoiceData)
    return response.data
  },

  update: async (id, invoiceData) => {
    const response = await api.put(`/invoices/${id}`, invoiceData)
    return response.data
  },

  getOverdue: async (days = 30) => {
    const response = await api.get('/invoices', { params: { overdue: true, days } })
    return response.data
  },
}


