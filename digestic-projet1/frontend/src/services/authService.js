import api from './api'

export const authService = {
  login: async (email) => {
    const response = await api.post('/auth/login', { email }, {
      withCredentials: true
    })
    return response.data
  },

  logout: async () => {
    const response = await api.post('/auth/logout', {}, {
      withCredentials: true
    })
    return response.data
  },

  getCurrentUser: async () => {
    const response = await api.get('/auth/me', {
      withCredentials: true
    })
    return response.data
  },
}


