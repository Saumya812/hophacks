/**
 * FindMyPal API client.
 * Talks to the FastAPI backend (default http://127.0.0.1:8000).
 */

const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

export function getOwnerToken(personId) {
  if (!personId) return ''
  try {
    return localStorage.getItem(`fmp-owner:${personId}`) || ''
  } catch {
    return ''
  }
}

export function saveOwnerToken(personId, token) {
  if (!personId || !token) return
  try {
    localStorage.setItem(`fmp-owner:${personId}`, token)
  } catch {
    /* ignore */
  }
}

async function request(path, options = {}) {
  const { ownerPersonId, timeoutMs, signal: outerSignal, headers: extraHeaders, ...rest } = options
  const ctrl = timeoutMs ? new AbortController() : null
  const timer = timeoutMs
    ? setTimeout(() => ctrl.abort(), timeoutMs)
    : null

  let signal = outerSignal
  if (ctrl && outerSignal) {
    outerSignal.addEventListener('abort', () => ctrl.abort(), { once: true })
    signal = ctrl.signal
  } else if (ctrl) {
    signal = ctrl.signal
  }

  const headers = {
    'Content-Type': 'application/json',
    ...(extraHeaders || {}),
  }
  const fromPath = path.match(/\/persons\/([0-9a-f-]{36})/i)
  const tok = getOwnerToken(ownerPersonId || fromPath?.[1])
  if (tok) headers['X-Owner-Token'] = tok

  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...rest,
      headers,
      signal,
    })

    let body = null
    const text = await res.text()
    if (text) {
      try {
        body = JSON.parse(text)
      } catch {
        body = text
      }
    }

    if (!res.ok) {
      const detail = body?.detail || body || res.statusText
      throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
    }

    return body
  } finally {
    if (timer) clearTimeout(timer)
  }
}

/** List persons with optional filters: name, location, age_min, age_max, status */
export function listPersons(params = {}) {
  const qs = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      qs.set(key, String(value))
    }
  })
  const suffix = qs.toString() ? `?${qs}` : ''
  return request(`/persons${suffix}`)
}

/** Fetch a single person by id */
export function getPerson(id) {
  return request(`/persons/${id}`)
}

/** Create a missing-person profile */
export async function createPerson(payload) {
  const created = await request('/persons', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
  if (created?.id && created?.owner_token) {
    saveOwnerToken(created.id, created.owner_token)
  }
  return created
}

/** List sightings for a person */
export function listSightings(personId) {
  return request(`/persons/${personId}/sightings`)
}

/** Submit a sighting / tip */
export function createSighting(personId, payload) {
  return request(`/persons/${personId}/sightings`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

/** Gemini natural-language search */
export function naturalSearch(query) {
  return request('/search/natural', {
    method: 'POST',
    body: JSON.stringify({ query }),
  })
}

/** Smart Person Search — scrape public sources + Gemini report */
export function lookupSearch(payload, { timeoutMs = 150_000 } = {}) {
  return request('/lookup/search', {
    method: 'POST',
    body: JSON.stringify(payload),
    timeoutMs,
  })
}

/** Face match against active case photos */
export function matchFace(payload) {
  return request('/faces/match', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

/** Duplicate case screening before create */
export function checkDuplicates(payload) {
  return request('/persons/check-duplicates', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

/** AI case summary */
export function getCaseSummary(personId) {
  return request(`/persons/${personId}/summary`)
}

export function refreshCaseSummary(personId) {
  return request(`/persons/${personId}/summary/refresh`, { method: 'POST' })
}

export { API_BASE }
