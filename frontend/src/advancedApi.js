/**
 * API helpers for advanced features.
 */
import { API_BASE, getOwnerToken } from './api.js'

async function request(path, options = {}) {
  const { ownerPersonId, ...rest } = options
  const headers = {
    'Content-Type': 'application/json',
    ...(rest.headers || {}),
  }
  const fromPath = path.match(/\/persons\/([0-9a-f-]{36})/i)
  const tok = getOwnerToken(ownerPersonId || fromPath?.[1])
  if (tok) headers['X-Owner-Token'] = tok

  const res = await fetch(`${API_BASE}${path}`, {
    ...rest,
    headers,
  })
  const text = await res.text()
  let body = null
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

export function getLiveTips(limit = 10) {
  return request(`/live/tips?limit=${limit}`)
}

export function getCityDashboard() {
  return request('/dashboard/city')
}

export function getBaltimoreCivic() {
  return request('/analytics/baltimore/civic')
}

export function getBaltimoreCameras(limit = 200) {
  return request(`/analytics/baltimore/cameras?limit=${limit}`)
}

export function getBaltimoreNearest(personId, { k = 5, maxM = 2500 } = {}) {
  const params = new URLSearchParams({
    k: String(k),
    max_m: String(maxM),
  })
  return request(`/analytics/baltimore/nearest/${personId}?${params}`)
}

export function getBaltimoreTipClusters(baltimoreOnly = true) {
  return request(
    `/analytics/baltimore/tip-clusters?baltimore_only=${baltimoreOnly ? 'true' : 'false'}`,
  )
}

export function getCaseActivity(personId, bucketHours = 24) {
  return request(`/analytics/case-activity/${personId}?bucket_hours=${bucketHours}`)
}

export function getPlatformMentions(personId) {
  return request(`/analytics/platform-mentions/${personId}`)
}

export function getCrossCasePatterns(radiusKm = 2) {
  return request(`/analytics/cross-case-patterns?radius_km=${radiusKm}`)
}

export function createNLAlert(payload) {
  return request('/alerts/natural', { method: 'POST', body: JSON.stringify(payload) })
}

export function createZipAlert(payload) {
  return request('/alerts/zip', { method: 'POST', body: JSON.stringify(payload) })
}

export function watchCase(payload) {
  return request('/alerts/watch', { method: 'POST', body: JSON.stringify(payload) })
}

export function getEngagement(personId) {
  return request(`/persons/${personId}/engagement`)
}

export function recordShare(personId) {
  return request(`/persons/${personId}/share`, { method: 'POST' })
}

export function getSocialKit(personId) {
  return request(`/persons/${personId}/social-kit`)
}

export function addCaseUpdate(personId, payload) {
  return request(`/persons/${personId}/updates`, { method: 'POST', body: JSON.stringify(payload) })
}

export function listCaseUpdates(personId) {
  return request(`/persons/${personId}/updates`)
}

export function listCaseSources(personId) {
  return request(`/persons/${personId}/sources`)
}

export function addCaseSource(personId, payload) {
  return request(`/persons/${personId}/sources`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function inviteCoordinator(personId, payload) {
  return request(`/persons/${personId}/coordinators`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function listCoordinators(personId) {
  return request(`/persons/${personId}/coordinators`)
}

export function markFound(personId, payload = {}) {
  return request(`/persons/${personId}/found`, { method: 'POST', body: JSON.stringify(payload) })
}

export function verifyPolice(personId, payload) {
  return request(`/persons/${personId}/verify-police`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function renewCase(personId) {
  return request(`/persons/${personId}/renew`, { method: 'POST' })
}

export function flagCase(personId, payload = {}) {
  return request(`/persons/${personId}/flag`, { method: 'POST', body: JSON.stringify(payload) })
}

export function listClusters(personId) {
  return request(`/persons/${personId}/clusters`)
}

export function rememberSearch(payload) {
  return request('/memory/remember', { method: 'POST', body: JSON.stringify(payload) })
}

export function recallSearch(participantKey) {
  return request(`/memory/recall?participant_key=${encodeURIComponent(participantKey)}`)
}

export function forgetSearch(participantKey) {
  return request(`/memory/forget?participant_key=${encodeURIComponent(participantKey)}`, {
    method: 'DELETE',
  })
}

export function requestCaseAudio(personId, payload = {}) {
  return request(`/persons/${personId}/audio`, { method: 'POST', body: JSON.stringify(payload) })
}
