import api from './api'

export const emailTemplateService = {
  list() {
    return api.get('/admin/email-templates').then((res) => res.data)
  },
  getCatalog() {
    return api.get('/admin/email-templates/catalog').then((res) => res.data)
  },
  get(templateKey) {
    return api
      .get(`/admin/email-templates/${encodeURIComponent(templateKey)}`)
      .then((res) => res.data)
  },
  update(templateKey, { subject_template, body_html_template }) {
    return api
      .put(`/admin/email-templates/${encodeURIComponent(templateKey)}`, {
        subject_template,
        body_html_template,
      })
      .then((res) => res.data)
  },
  createCustom({ template_key, subject_template, body_html_template }) {
    return api
      .post('/admin/email-templates', {
        template_key,
        subject_template,
        body_html_template,
      })
      .then((res) => res.data)
  },
}
