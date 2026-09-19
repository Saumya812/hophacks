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

export { API_BASE }
