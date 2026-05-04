import api from './api'

export const creditNoteService = {
  /** @returns {Promise<object[]>} */
  listByInvoiceId: async (invoiceId) => {
    const { data } = await api.get(`/invoices/${invoiceId}/credit-notes`)
    return Array.isArray(data) ? data : []
  },

  /** @returns {Promise<object>} avoir créé */
  issue: async (invoiceId, body) => {
    const { data } = await api.post(`/invoices/${invoiceId}/credit-notes`, body)
    return data
  },

  /** Avoir total uniquement (sans partial_lines) */
  issueTotal: async (invoiceId, { correction_reason }) => {
    return creditNoteService.issue(invoiceId, { correction_reason })
  },

  /** Télécharge le PDF VosFactures pour un avoir enregistré en base */
  downloadVosFacturesPdf: async (creditNoteId) => {
    try {
      const response = await api.get(`/credit-notes/${creditNoteId}/pdf`, {
        responseType: 'blob',
      })
      const disp = response.headers['content-disposition']
      let filename = 'avoir.pdf'
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
