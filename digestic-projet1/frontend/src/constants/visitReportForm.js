/** Options « semaine de retour prévu » : 1…10 semaines. */
export const WEEKS_UNTIL_RETURN_OPTIONS = Array.from({ length: 10 }, (_, i) => {
  const n = i + 1
  return { value: String(n), label: n === 1 ? 'Dans 1 semaine' : `Dans ${n} semaines` }
})

export const VISIT_NOT_COMPLETED_REASON_LABELS = {
  pharmacy_closed: 'Pharmacie fermée',
  owner_absent: 'Titulaire absent',
  refus: 'Refus',
}

export function getVisitNotCompletedReasonLabel(code) {
  if (!code) return '-'
  return VISIT_NOT_COMPLETED_REASON_LABELS[code] || code
}

/** Message d’erreur (aligné sur l’API) si le statut est « non effectuée » sans raison. */
export const MSG_VISIT_NOT_COMPLETED_REASON_REQUIRED =
  "La raison est obligatoire lorsque la visite n'est pas effectuée."

/** @returns {string | null} message d'erreur ou null si valide */
export function validateVisitNotCompletedReason(visitStatus, visitNotCompletedReason) {
  if (visitStatus === 'not_completed' && !String(visitNotCompletedReason || '').trim()) {
    return MSG_VISIT_NOT_COMPLETED_REASON_REQUIRED
  }
  return null
}

export function formatExpectedReturnIso(year, week) {
  if (year == null || week == null) return null
  return `Semaine ISO ${week} · ${year}`
}
