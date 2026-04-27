/**
 * Construit les query string pour des paramètres répétés (ex. ?a=1&a=2) — GET listes paginées.
 * @param {URLSearchParams} sp
 * @param {string} key
 * @param {string|string[]|undefined|null} val
 */
export function appendRepeatedQuery(sp, key, val) {
  if (Array.isArray(val)) {
    for (const p of val) {
      const t = String(p).trim()
      if (t) {
        sp.append(key, t)
      }
    }
  } else if (val !== undefined && val !== null && String(val).trim() !== '') {
    sp.append(key, String(val).trim())
  }
}

/**
 * @param {object} p
 * @param {Record<string, unknown>} p.merged - déjà { ...defaultList, ...params }
 * @param {string[]} p.repeatedParamKeys - clés à traiter par appendRepeatedQuery (retirées du reste)
 * @param {(sp: URLSearchParams, k: string, v: unknown) => void} [p.appendEntry] - append d’une entrée rest ; défaut: skip empty, append string
 */
export function buildSearchParamsForPagedList({
  merged,
  repeatedParamKeys = [],
  appendEntry = (sp, k, v) => {
    if (v === undefined || v === null || v === '') {
      return
    }
    sp.append(k, String(v))
  },
}) {
  const rest = { ...merged }
  const repeated = {}
  for (const rk of repeatedParamKeys) {
    if (Object.prototype.hasOwnProperty.call(rest, rk)) {
      repeated[rk] = rest[rk]
      delete rest[rk]
    }
  }
  const sp = new URLSearchParams()
  for (const [k, v] of Object.entries(rest)) {
    appendEntry(sp, k, v)
  }
  for (const rk of repeatedParamKeys) {
    appendRepeatedQuery(sp, rk, repeated[rk])
  }
  return sp
}
