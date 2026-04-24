/** Libellés pour `status` côté API (Sage / métier) */
export const PHARMACY_STATUS_LABELS = {
  actif: 'Actif',
  desactive: 'Désactivé',
  standby: 'Stand by',
  autre: 'Autre',
}

export function getPharmacyStatusLabel (status) {
  if (status == null || status === '') return '—'
  const s = String(status)
  return PHARMACY_STATUS_LABELS[s] || s
}

export const PHARMACY_STATUS_OPTIONS = [
  { value: 'actif', label: 'Actif' },
  { value: 'desactive', label: 'Désactivé' },
  { value: 'standby', label: 'Stand by' },
  { value: 'autre', label: 'Autre' },
]
