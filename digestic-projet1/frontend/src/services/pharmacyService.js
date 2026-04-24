import api from './api'

export const pharmacyService = {
  getAll: async () => {
    const response = await api.get('/pharmacies')
    return response.data
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
}


