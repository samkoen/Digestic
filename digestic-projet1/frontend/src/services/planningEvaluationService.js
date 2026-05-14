import api from './api'

export const planningEvaluationService = {
  /**
   * @param {{
   *   startDate: string,
   *   endDate: string,
   *   commercialId?: string | null,
   *   planningWeightsRevisionId?: string | null,
   *   pureAutoPlanningWeightsOnly?: boolean,
   * }} params ISO dates yyyy-MM-dd
   */
  getEvaluation: async ({
    startDate,
    endDate,
    commercialId,
    planningWeightsRevisionId,
    pureAutoPlanningWeightsOnly,
  }) => {
    const params = { start_date: startDate, end_date: endDate }
    if (commercialId) params.commercial_id = commercialId
    if (planningWeightsRevisionId) params.planning_weights_revision_id = planningWeightsRevisionId
    if (pureAutoPlanningWeightsOnly === false) params.pure_auto_planning_weights_only = false
    const response = await api.get('/planning/evaluation', {
      params,
      withCredentials: true,
    })
    return response.data
  },
}
