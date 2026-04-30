import api from './api'
import { buildSearchParamsForPagedList } from '../utils/httpQueryParams'

const DEFAULT_DELIVERY_NOTE_LIST = {
  page: 1,
  page_size: 20,
  sort: 'deliveryDate',
  order: 'desc',
}

export async function fetchDeliveryNotesPage(params = {}) {
  const merged = { ...DEFAULT_DELIVERY_NOTE_LIST, ...params }
  const sp = buildSearchParamsForPagedList({
    merged,
    repeatedParamKeys: ['pharmacy_id', 'commercial_id'],
  })
  const { data } = await api.get('/delivery-notes', { params: sp })
  return data
}

export const deliveryNoteService = {
  getList: fetchDeliveryNotesPage,

  getAll: async (params = {}) => {
    const data = await fetchDeliveryNotesPage({
      ...params,
      page: 1,
      page_size: 500,
    })
    return data.items || []
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

  /** Dépôt-vente → statut « en attente » (pending). */
  validateDepotVente: async (noteId) => {
    const response = await api.post(`/delivery-notes/${noteId}/valider-depot-vente`)
    return response.data
  },

  /**
   * Télécharge le PDF du bon de livraison (généré côté serveur).
   */
  downloadPdf: async (noteId) => {
    try {
      const response = await api.get(`/delivery-notes/${noteId}/pdf`, { responseType: 'blob' })
      const disp = response.headers['content-disposition']
      let filename = 'bon_livraison.pdf'
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
