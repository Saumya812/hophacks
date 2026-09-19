/**
 * Shared helpers for volunteer case UX (dates, URLs, bookmarks).
 */

const SAVED_KEY = 'fmp-saved-case-ids'

/** Format a date-only YYYY-MM-DD without timezone shift; unknown stays unknown. */
export function formatEventDate(value) {
  if (value == null || value === '') return null
  const s = String(value).trim()
  const m = s.match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (m) {
    const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]))
    if (Number.isNaN(d.getTime())) return null
    return d.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }
  const d = new Date(s)
  if (Number.isNaN(d.getTime())) return null
  return d.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

/** Format a timestamp for display; returns null if missing/invalid (never invent "today"). */
export function formatEventDateTime(value) {
  if (value == null || value === '') return null
  const s = String(value).trim()
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return formatEventDate(s)
  const d = new Date(s)
  if (Number.isNaN(d.getTime())) return null
  return d.toLocaleString()
}

/** Only allow http(s) URLs for external links. */
export function safeHttpUrl(raw) {
  const s = (raw || '').trim()
  if (!s) return null
  try {
    const u = new URL(s)
    if (u.protocol !== 'http:' && u.protocol !== 'https:') return null
    return u.toString()
  } catch {
    return null
  }
}

export function readSavedCaseIds() {
  try {
    const raw = localStorage.getItem(SAVED_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return [...new Set(parsed.map((id) => String(id)).filter(Boolean))]
  } catch {
    return []
  }
}

export function writeSavedCaseIds(ids) {
  try {
    localStorage.setItem(SAVED_KEY, JSON.stringify([...new Set(ids.map(String))]))
    return true
  } catch {
    return false
  }
}

export function isCaseSaved(personId) {
  if (!personId) return false
  return readSavedCaseIds().includes(String(personId))
}

export function toggleSavedCase(personId) {
  const id = String(personId || '')
  if (!id) return { saved: false, ids: readSavedCaseIds() }
  const ids = readSavedCaseIds()
  const idx = ids.indexOf(id)
  let next
  if (idx >= 0) {
    next = ids.filter((x) => x !== id)
  } else {
    next = [...ids, id]
  }
  writeSavedCaseIds(next)
  return { saved: idx < 0, ids: next }
}

export function validateAgeRange(ageMin, ageMax) {
  const min = ageMin === '' || ageMin == null ? null : Number(ageMin)
  const max = ageMax === '' || ageMax == null ? null : Number(ageMax)
  if (min != null && (Number.isNaN(min) || min < 0 || min > 150)) {
    return { ok: false, error: 'Minimum age must be between 0 and 150.' }
  }
  if (max != null && (Number.isNaN(max) || max < 0 || max > 150)) {
    return { ok: false, error: 'Maximum age must be between 0 and 150.' }
  }
  if (min != null && max != null && max < min) {
    return { ok: false, error: 'Maximum age must be greater than or equal to minimum age.' }
  }
  return { ok: true, ageMin: min, ageMax: max }
}

/**
 * Stable sort key for timeline events. Date-only values use local midnight
 * (no UTC shift). Unknown / invalid dates sort last and are never replaced with today.
 */
export function eventSortKey(value) {
  if (value == null || value === '') return Number.POSITIVE_INFINITY
  const s = String(value).trim()
  const m = s.match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (m) {
    const t = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])).getTime()
    return Number.isNaN(t) ? Number.POSITIVE_INFINITY : t
  }
  const t = new Date(s).getTime()
  return Number.isNaN(t) ? Number.POSITIVE_INFINITY : t
}

/** Compare two event dates ascending; unknown last; tie-break by id. */
export function compareTimelineEvents(a, b) {
  const ka = eventSortKey(a?.when)
  const kb = eventSortKey(b?.when)
  if (ka !== kb) return ka - kb
  return String(a?.id || '').localeCompare(String(b?.id || ''))
}

/**
 * Label a case_updates row. Only "Family update" when authorship is established
 * (author email matches the case contact email).
 */
export function caseUpdateLabel(update, person) {
  const author = (update?.author_email || '').trim().toLowerCase()
  const contact = (person?.contact_email || '').trim().toLowerCase()
  if (author && contact && author === contact) return 'Family update'
  return 'Case update'
}
