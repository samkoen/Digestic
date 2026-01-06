import api from './api'

export const commercialMaterialService = {
  getAll: async (activeOnly = false) => {
    const response = await api.get('/commercial-materials', { 
      params: { active_only: activeOnly } 
    })
    return response.data
  },

  getById: async (id) => {
    const response = await api.get(`/commercial-materials/${id}`)
    return response.data
  },

  create: async (materialData) => {
    const response = await api.post('/commercial-materials', materialData)
    return response.data
  },

  update: async (id, materialData) => {
    const response = await api.put(`/commercial-materials/${id}`, materialData)
    return response.data
  },
}


