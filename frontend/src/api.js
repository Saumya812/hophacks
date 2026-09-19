/**
 * FindMyPal API client.
 * Talks to the FastAPI backend (default http://127.0.0.1:8000).
 */

const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
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
export function createPerson(payload) {
  return request('/persons', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
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
export function lookupSearch(payload) {
  return request('/lookup/search', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

/** Fetch a cached lookup report by id */
export function getLookupReport(reportId) {
  return request(`/lookup/report/${reportId}`)
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
