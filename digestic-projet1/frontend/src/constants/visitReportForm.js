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

export function formatExpectedReturnIso(year, week) {
  if (year == null || week == null) return null
  return `Semaine ISO ${week} · ${year}`
}
