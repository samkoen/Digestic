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
