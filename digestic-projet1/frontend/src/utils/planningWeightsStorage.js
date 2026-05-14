const STORAGE_KEY = 'digestic_planning_weights'

export function loadPlanningWeightsOverrides() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const data = JSON.parse(raw)
    if (!data || typeof data !== 'object' || Array.isArray(data)) return null
    return data
  } catch {
    return null
  }
}

/** Enregistre l’objet complet utilisé lors des POST `/planning/run` (`body.weights`). */
export function savePlanningWeights(weightsObj) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(weightsObj))
}

export function clearPlanningWeightsOverrides() {
  localStorage.removeItem(STORAGE_KEY)
}
