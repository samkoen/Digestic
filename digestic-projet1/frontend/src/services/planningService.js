import api from './api'

export const planningService = {
  run: async (payload = {}) => {
    const response = await api.post('/planning/run', payload, {
      withCredentials: true,
    })
    return response.data
  },

  getWeightDefaults: async () => {
    const response = await api.get('/planning/weights-defaults', {
      withCredentials: true,
    })
    return response.data
  },

  /** Révision active + snapshot effectif (poids moteur planning, pas note terrain v1). */
  getActiveWeightsConfig: async () => {
    const response = await api.get('/planning/weights-config/active', {
      withCredentials: true,
    })
    return response.data
  },

  listWeightsRevisions: async (limit = 50) => {
    const response = await api.get('/planning/weights-revisions', {
      params: { limit },
      withCredentials: true,
    })
    return response.data
  },

  createWeightsRevision: async ({ weights, label, setActive = true }) => {
    const response = await api.post(
      '/planning/weights-revisions',
      { weights, label: label || null, set_active: setActive },
      { withCredentials: true },
    )
    return response.data
  },

  setActiveWeightsRevision: async (revisionId) => {
    const response = await api.put(
      '/planning/weights-config/active',
      { revision_id: revisionId },
      { withCredentials: true },
    )
    return response.data
  },

  listPlanningRuns: async (limit = 40) => {
    const response = await api.get('/planning/runs', {
      params: { limit },
      withCredentials: true,
    })
    return response.data
  },

  getRuntimeConfig: async () => {
    const response = await api.get('/planning/runtime-config', {
      withCredentials: true,
    })
    return response.data
  },

  putRuntimeConfig: async ({ manualPlanningSegmentMode }) => {
    const response = await api.put(
      '/planning/runtime-config',
      { manual_planning_segment_mode: manualPlanningSegmentMode },
      { withCredentials: true },
    )
    return response.data
  },
}
