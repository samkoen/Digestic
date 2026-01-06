import api from './api'

export const visitService = {
  getAll: async (filters = {}) => {
    const response = await api.get('/visits', { params: filters })
    return response.data
  },

  getById: async (id) => {
    const response = await api.get(`/visits/${id}`)
    return response.data
  },

  create: async (visitData) => {
    const response = await api.post('/visits', visitData)
    return response.data
  },

  update: async (id, visitData) => {
    const response = await api.put(`/visits/${id}`, visitData)
    return response.data
  },

  delete: async (id) => {
    const response = await api.delete(`/visits/${id}`)
    return response.data
  },
}


