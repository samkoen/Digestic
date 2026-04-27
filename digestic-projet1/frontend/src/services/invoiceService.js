import api from './api'
import { buildSearchParamsForPagedList } from '../utils/httpQueryParams'

const DEFAULT_INVOICE_LIST = {
  page: 1,
  page_size: 20,
  sort: 'issueDate',
  order: 'asc',
}

/**
 * @param {Record<string, unknown>} params — page, page_size, sort, order, filtres
 * @returns {Promise<{ items: any[], total: number, page: number, page_size: number }>}
 */
export async function fetchInvoicesPage(params = {}) {
  const merged = { ...DEFAULT_INVOICE_LIST, ...params }
  const sp = buildSearchParamsForPagedList({ merged })
  const { data } = await api.get('/invoices', { params: sp })
  return data
}

export const invoiceService = {
  /**
   * Liste paginée (GET avec `page` — réponse { items, total, … }).
   */
  getList: fetchInvoicesPage,
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

  /**
   * Télécharge le PDF VosFactures (backend proxy, cookie de session).
   */
  downloadVosFacturesPdf: async (id) => {
    try {
      const response = await api.get(`/invoices/${id}/pdf`, { responseType: 'blob' })
      const disp = response.headers['content-disposition']
      let filename = 'facture.pdf'
      if (disp) {
        const utf = /filename\*=UTF-8''([^;\n]+)/i.exec(disp)
        const ascii = /filename="([^"]+)"/i.exec(disp)
        if (utf) {
          filename = decodeURIComponent(utf[1].trim())
        } else if (ascii) {
          filename = ascii[1].trim()
        }
      }
      const url = window.URL.createObjectURL(response.data)
      try {
        const a = document.createElement('a')
        a.href = url
        a.download = filename
        document.body.appendChild(a)
        a.click()
        a.remove()
      } finally {
        window.URL.revokeObjectURL(url)
      }
    } catch (e) {
      if (e.response?.data instanceof Blob) {
        const t = await e.response.data.text()
        let msg = t.slice(0, 400)
        try {
          const j = JSON.parse(t)
          if (j.error) msg = j.error
        } catch {
          /* texte non JSON */
        }
        throw new Error(msg || e.message)
      }
      throw e
    }
  },
}


