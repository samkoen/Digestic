/**
 * Modes de paiement (pharmacie / dépôt) : mêmes chaînes qu’en base et à l’API.
 */
export const PAYMENT_MODES = [
  'prélèvement SEPA 30 jours',
  'prélèvement SEPA 60 jours',
  'virement 30 jours',
  'virement 60 jours',
  'dépôt vente',
]

export const DEFAULT_PAYMENT_MODE = 'virement 30 jours'

/** Prélèvement SEPA (30 ou 60 j) : RIB obligatoire en saisie pharmacie. */
export function isPrelevementSepa(paymentMode) {
  if (!paymentMode || typeof paymentMode !== 'string') return false
  return paymentMode.trim().toLowerCase().startsWith('prélèvement sepa')
}
