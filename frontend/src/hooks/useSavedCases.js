/**
 * Device-local saved cases (localStorage only — not public watchers).
 */
import { useCallback, useEffect, useState, useSyncExternalStore } from 'react'
import {
  isCaseSaved,
  readSavedCaseIds,
  toggleSavedCase,
  writeSavedCaseIds,
} from '../lib/caseHelpers.js'

const listeners = new Set()

function emit() {
  listeners.forEach((l) => l())
}

function subscribe(cb) {
  listeners.add(cb)
  const onStorage = (e) => {
    if (e.key === 'fmp-saved-case-ids') cb()
  }
  window.addEventListener('storage', onStorage)
  return () => {
    listeners.delete(cb)
    window.removeEventListener('storage', onStorage)
  }
}

function getSnapshot() {
  return readSavedCaseIds().join(',')
}

export function useSavedCases() {
  const snap = useSyncExternalStore(subscribe, getSnapshot, () => '')
  const ids = snap ? snap.split(',').filter(Boolean) : []

  const toggle = useCallback((personId) => {
    const result = toggleSavedCase(personId)
    emit()
    return result
  }, [])

  const isSaved = useCallback((personId) => ids.includes(String(personId)), [ids])

  const clearAll = useCallback(() => {
    writeSavedCaseIds([])
    emit()
  }, [])

  return { savedIds: ids, isSaved, toggle, clearAll, count: ids.length }
}

export function useCaseSaved(personId) {
  const { isSaved, toggle } = useSavedCases()
  const [saved, setSaved] = useState(() => isCaseSaved(personId))

  useEffect(() => {
    setSaved(isSaved(personId))
  }, [personId, isSaved])

  const onToggle = useCallback(() => {
    const r = toggle(personId)
    setSaved(r.saved)
    return r
  }, [personId, toggle])

  return { saved, toggle: onToggle }
}
