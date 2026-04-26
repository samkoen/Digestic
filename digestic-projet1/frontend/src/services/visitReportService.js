import api from './api'

export const visitReportService = {
  getAll: async (filters = {}) => {
    const response = await api.get('/visit-reports', { params: filters })
    return response.data
  },

  getById: async (id) => {
    const response = await api.get(`/visit-reports/${id}`)
    return response.data
  },

  create: async (reportData) => {
    const response = await api.post('/visit-reports', reportData)
    return response.data
  },

  update: async (id, reportData) => {
    const response = await api.put(`/visit-reports/${id}`, reportData)
    return response.data
  },

  sync: async () => {
    const response = await api.post('/visit-reports/sync')
    return response.data
  },

  /** @param {File} file */
  uploadMedia: async (file) => {
    const body = new FormData()
    body.append('file', file)
    const res = await fetch('/api/visit-reports/upload-media', {
      method: 'POST',
      body,
      credentials: 'include',
    })
    if (!res.ok) {
      const text = await res.text()
      throw new Error(text || res.statusText)
    }
    const data = await res.json()
    return data.url
  },
}


