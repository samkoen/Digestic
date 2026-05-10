import { PHARMACY_STATUS_OPTIONS } from '../constants/pharmacyStatus'

/** Libellés alignés sur `InvoiceDataCells.jsx` (liste factures) ; `value` = clé API. */
export const INVOICE_STATUS_FILTER_OPTIONS = [
  { value: 'pending', label: 'En attente' },
  { value: 'overdue', label: 'En retard' },
  { value: 'paid', label: 'Payée' },
  { value: 'credited', label: 'Avoir émis' },
  { value: 'cancelled', label: 'Annulée' },
]

/** Aligné sur `DeliveryNoteFilterCells` / `DeliveryNoteDataCells` ; `value` = clé API. */
export const DEPOSIT_STATUS_FILTER_OPTIONS = [
  { value: 'pending', label: 'En attente' },
  { value: 'validated', label: 'Validé (visite)' },
  { value: 'sent', label: 'Envoyé' },
  { value: 'confirmed', label: 'Confirmé' },
  { value: 'fully_invoiced', label: 'Facturé' },
  { value: 'draft', label: 'Brouillon' },
  { value: 'depot-vente', label: 'Dépôt-vente' },
  { value: 'cancelled', label: 'Annulé' },
]

/** Même entrées que le tableau pharmacies (`getPharmacyStatusLabel`). */
export { PHARMACY_STATUS_OPTIONS as PHARMACY_STATUS_FILTER_OPTIONS }

export const ADVANCED_FILTER_COMBINE = [
  { value: 'and', label: 'Toutes les conditions (ET)' },
  { value: 'or', label: 'Au moins une condition (OU)' },
]

export const SUBJECT_OPTIONS = [
  { value: 'pharmacy', label: 'Pharmacie' },
  { value: 'invoice', label: 'Facture (liée à la pharmacie)' },
  { value: 'delivery_note', label: 'Bon de livraison / BL (dépôt)' },
]

const OPS_EQ = [
  { value: '=', label: 'égal' },
  { value: '!=', label: 'différent de' },
]

const OPS_ALL = [
  ...OPS_EQ,
  { value: '<', label: 'plus petit que (<)' },
  { value: '>', label: 'plus grand que (>)' },
  { value: '<=', label: '≤' },
  { value: '>=', label: '≥' },
]

export const FIELD_OPTIONS_BY_SUBJECT = {
  pharmacy: [
    { value: 'pharmacy_status', label: 'Statut pharmacie', ops: OPS_EQ, valueSelect: 'pharmacy_status' },
    { value: 'city', label: 'Ville', ops: OPS_EQ, valueHint: 'texte' },
    { value: 'postal_code', label: 'Code postal', ops: OPS_EQ, valueHint: 'texte' },
    { value: 'next_visit_date', label: 'Prochaine visite (date)', ops: OPS_ALL, valueHint: 'YYYY-MM-DD — < = avant' },
    { value: 'created_at', label: 'Date de création (jour)', ops: OPS_ALL, valueHint: 'YYYY-MM-DD' },
  ],
  invoice: [
    { value: 'status', label: 'Statut facture', ops: OPS_EQ, valueSelect: 'invoice_status' },
    { value: 'issue_date', label: 'Date d’émission', ops: OPS_ALL, valueHint: 'YYYY-MM-DD' },
    { value: 'due_date', label: 'Date d’échéance', ops: OPS_ALL, valueHint: 'YYYY-MM-DD' },
    { value: 'days_overdue', label: 'Jours de retard', ops: OPS_ALL, valueHint: 'nombre entier' },
    { value: 'amount', label: 'Montant TTC', ops: OPS_ALL, valueHint: 'nombre' },
  ],
  delivery_note: [
    { value: 'status', label: 'Statut BL', ops: OPS_EQ, valueSelect: 'deposit_status' },
    { value: 'delivery_date', label: 'Date de livraison', ops: OPS_ALL, valueHint: 'YYYY-MM-DD' },
    { value: 'bottles_count', label: 'Nombre de bouteilles', ops: OPS_ALL, valueHint: 'entier' },
  ],
}

export function getFieldMeta(subject, field) {
  const list = FIELD_OPTIONS_BY_SUBJECT[subject] || []
  return list.find((x) => x.value === field) || null
}

/** @param {'pharmacy_status' | 'invoice_status' | 'deposit_status' | null | undefined} kind */
export function optionsForValueSelect(kind) {
  if (kind === 'pharmacy_status') {
    return PHARMACY_STATUS_OPTIONS
  }
  if (kind === 'invoice_status') {
    return INVOICE_STATUS_FILTER_OPTIONS
  }
  if (kind === 'deposit_status') {
    return DEPOSIT_STATUS_FILTER_OPTIONS
  }
  return null
}

export function emptyPayload() {
  return { combine: 'and', conditions: [] }
}

export function emptyCondition() {
  return {
    _key: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
    subject: 'pharmacy',
    field: 'pharmacy_status',
    op: '=',
    value: PHARMACY_STATUS_OPTIONS[0]?.value || 'actif',
  }
}
