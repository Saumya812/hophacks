/**
 * Focused unit checks for volunteer case helpers (no test runner required).
 * Run: node --test frontend/src/lib/caseHelpers.test.js
 */
import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import {
  caseUpdateLabel,
  compareTimelineEvents,
  eventSortKey,
  formatEventDate,
  formatEventDateTime,
  readSavedCaseIds,
  safeHttpUrl,
  toggleSavedCase,
  validateAgeRange,
  writeSavedCaseIds,
} from './caseHelpers.js'

describe('formatEventDate / date-only', () => {
  it('formats YYYY-MM-DD without inventing today', () => {
    const s = formatEventDate('2024-01-15')
    assert.ok(s && s.includes('2024'))
    assert.equal(formatEventDate(null), null)
    assert.equal(formatEventDate(''), null)
    assert.equal(formatEventDate('not-a-date'), null)
  })

  it('formatEventDateTime treats date-only like formatEventDate', () => {
    assert.equal(formatEventDateTime('2024-06-01'), formatEventDate('2024-06-01'))
  })
})

describe('eventSortKey / timeline order', () => {
  it('sorts chronologically with unknown last', () => {
    const items = [
      { id: 'b', when: '2024-03-01' },
      { id: 'a', when: null },
      { id: 'c', when: '2023-12-01' },
    ]
    items.sort(compareTimelineEvents)
    assert.deepEqual(
      items.map((i) => i.id),
      ['c', 'b', 'a'],
    )
    assert.equal(eventSortKey(null), Number.POSITIVE_INFINITY)
  })
})

describe('safeHttpUrl', () => {
  it('allows http(s) only', () => {
    assert.ok(safeHttpUrl('https://example.com/case?id=1'))
    assert.ok(safeHttpUrl('http://example.com'))
    assert.equal(safeHttpUrl('javascript:alert(1)'), null)
    assert.equal(safeHttpUrl('ftp://files.example'), null)
    assert.equal(safeHttpUrl(''), null)
  })
})

describe('validateAgeRange', () => {
  it('validates ranges', () => {
    assert.equal(validateAgeRange(20, 30).ok, true)
    assert.equal(validateAgeRange('', '').ok, true)
    assert.equal(validateAgeRange(40, 20).ok, false)
    assert.equal(validateAgeRange(-1, 10).ok, false)
    assert.equal(validateAgeRange(0, 150).ok, true)
  })
})

describe('bookmarks / localStorage', () => {
  it('parses and toggles ids; tolerates corrupt storage', () => {
    globalThis.localStorage = (() => {
      let store = {}
      return {
        getItem: (k) => (k in store ? store[k] : null),
        setItem: (k, v) => {
          store[k] = String(v)
        },
        removeItem: (k) => {
          delete store[k]
        },
        _dump: () => store,
        _setRaw: (k, v) => {
          store[k] = v
        },
      }
    })()

    writeSavedCaseIds([])
    assert.deepEqual(readSavedCaseIds(), [])
    toggleSavedCase('abc')
    assert.deepEqual(readSavedCaseIds(), ['abc'])
    toggleSavedCase('abc')
    assert.deepEqual(readSavedCaseIds(), [])

    globalThis.localStorage._setRaw('fmp-saved-case-ids', '{not-json')
    assert.deepEqual(readSavedCaseIds(), [])

    globalThis.localStorage._setRaw('fmp-saved-case-ids', JSON.stringify({ x: 1 }))
    assert.deepEqual(readSavedCaseIds(), [])
  })

  it('handles unavailable localStorage', () => {
    globalThis.localStorage = {
      getItem() {
        throw new Error('blocked')
      },
      setItem() {
        throw new Error('blocked')
      },
    }
    assert.deepEqual(readSavedCaseIds(), [])
    assert.equal(writeSavedCaseIds(['a']), false)
  })
})

describe('caseUpdateLabel', () => {
  it('uses Family update only when authorship matches', () => {
    assert.equal(
      caseUpdateLabel({ author_email: 'a@b.com' }, { contact_email: 'a@b.com' }),
      'Family update',
    )
    assert.equal(caseUpdateLabel({ author_email: 'a@b.com' }, { contact_email: null }), 'Case update')
    assert.equal(caseUpdateLabel({}, { contact_email: 'a@b.com' }), 'Case update')
  })
})

describe('backward compatibility', () => {
  it('safe helpers tolerate missing person source fields', () => {
    assert.equal(safeHttpUrl(undefined), null)
    assert.equal(formatEventDate(undefined), null)
    assert.equal(caseUpdateLabel(undefined, undefined), 'Case update')
  })
})
