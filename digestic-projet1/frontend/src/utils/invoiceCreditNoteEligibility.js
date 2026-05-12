/** Marquer comme payée (saisie encaissement) : factures uniquement, pas les documents avoir ni clôturées. */
export function canMarkInvoicePaid(invoice) {
  if (!invoice) return false
  if (invoice.row_kind === 'credit_note') return false
  const st = String(invoice.status || '')
    .toLowerCase()
    .trim()
  if (st === 'paid' || st === 'credited' || st === 'cancelled') return false
  return true
}

/**
 * Afficher le bouton/icône relance (liste ou fiche). L’API refusera l’envoi si l’échéance
 * n’est pas encore dépassée.
 */
export function canOfferUnpaidReminderAction(invoice) {
  if (!invoice || invoice.row_kind === 'credit_note') return false
  const st = String(invoice.status || '')
    .toLowerCase()
    .trim()
  return st === 'pending' || st === 'overdue'
}

/**
 * Relance réellement envoyable : échéance dépassée d’au moins un jour (comme le serveur).
 */
export function canSendUnpaidReminder(invoice) {
  if (!invoice || invoice.row_kind === 'credit_note') return false
  const st = String(invoice.status || '')
    .toLowerCase()
    .trim()
  if (st === 'paid' || st === 'credited' || st === 'cancelled') return false
  if (st === 'overdue') return true
  if (st !== 'pending') return false
  if (Number(invoice.days_overdue ?? 0) >= 1) return true
  try {
    const chunk = String(invoice.due_date || '').slice(0, 10)
    if (!/^\d{4}-\d{2}-\d{2}$/.test(chunk)) return false
    const [y, m, d] = chunk.split('-').map((x) => parseInt(x, 10))
    const due = new Date(y, m - 1, d)
    const t = new Date()
    const today = new Date(t.getFullYear(), t.getMonth(), t.getDate())
    const diffDays = Math.floor((today - due) / 86400000)
    return diffDays >= 1
  } catch {
    return false
  }
}

/** Avoir réel ou mock via VosFactures : facture doit porter un id document VF. */
export function canIssueTotalCreditNote(invoice) {
  if (!invoice) return false
  const st = String(invoice.status || '')
    .toLowerCase()
    .trim()
  if (st === 'credited' || st === 'cancelled') return false
  const p = (invoice.external_provider || '').toLowerCase().trim()
  const okProv = p === 'vosfactures' || p === 'vosfactures_mock'
  const extId = String(invoice.external_invoice_id ?? '').trim()
  return Boolean(okProv && extId)
}
