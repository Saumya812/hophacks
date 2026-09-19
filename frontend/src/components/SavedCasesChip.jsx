/**
 * “Saved on this device” chip — always shown under the gallery.
 * Expands when you have saved cases (save from a case modal).
 */
import { useMemo, useState } from 'react'
import { useSavedCases } from '../hooks/useSavedCases.js'
import { formatEventDate } from '../lib/caseHelpers.js'

export default function SavedCasesChip({ persons = [], onOpen }) {
  const { savedIds, count, toggle } = useSavedCases()
  const [open, setOpen] = useState(false)

  const savedPeople = useMemo(() => {
    const byId = new Map(persons.map((p) => [String(p.id), p]))
    return savedIds.map((id) => byId.get(String(id))).filter(Boolean)
  }, [persons, savedIds])

  const missing = count - savedPeople.length

  return (
    <div className="mt-6 flex w-full max-w-md flex-col items-center">
      <button
        type="button"
        className="inline-flex items-center gap-2 rounded-full border border-border bg-white px-5 py-2.5 text-sm font-medium text-ink shadow-card transition-colors hover:bg-stone"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="inline-block h-2 w-2 rounded-full bg-sage" aria-hidden />
        {count === 0
          ? 'Saved on this device'
          : `${count} saved on this device`}
        <span className="text-text-muted">{open ? '▴' : '▾'}</span>
      </button>

      {open && (
        <div className="mt-3 w-full rounded-xl border border-border bg-white p-4 text-left shadow-card">
          <p className="mb-3 text-xs text-text-muted">
            Stored only in this browser — not the same as public watchers.
          </p>

          {count === 0 ? (
            <p className="text-sm leading-relaxed text-text-muted">
              Nothing saved yet. Open a gallery frame → use{' '}
              <span className="font-medium text-ink">Save</span> in the case popup.
            </p>
          ) : savedPeople.length === 0 ? (
            <p className="text-sm text-text-muted">
              {count} saved case{count === 1 ? '' : 's'} no longer in the active list.
            </p>
          ) : (
            <ul className="space-y-2">
              {savedPeople.map((p) => (
                <li key={p.id} className="flex items-center gap-2">
                  <button
                    type="button"
                    className="flex min-w-0 flex-1 items-center gap-2 rounded-lg px-2 py-1.5 text-left hover:bg-cream"
                    onClick={() =>
                      onOpen?.({ person: p, gallerySrc: p.photo_url || null })
                    }
                  >
                    <div className="h-9 w-9 shrink-0 overflow-hidden rounded-md bg-stone">
                      {p.photo_url ? (
                        <img src={p.photo_url} alt="" className="h-full w-full object-cover" />
                      ) : (
                        <div className="flex h-full items-center justify-center font-display text-sm text-ink/30">
                          {(p.name || '?').charAt(0)}
                        </div>
                      )}
                    </div>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-ink">{p.name}</p>
                      <p className="truncate text-[11px] text-text-muted">
                        {p.last_seen_location}
                        {p.last_seen_date
                          ? ` · ${formatEventDate(p.last_seen_date) || p.last_seen_date}`
                          : ''}
                      </p>
                    </div>
                  </button>
                  <button
                    type="button"
                    className="shrink-0 rounded px-2 py-1 text-[11px] text-text-muted hover:bg-cream hover:text-ink"
                    onClick={() => toggle(p.id)}
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          )}

          {missing > 0 && savedPeople.length > 0 && (
            <p className="mt-2 text-[11px] text-text-muted">
              {missing} saved id{missing === 1 ? '' : 's'} not in the current active list.
            </p>
          )}
        </div>
      )}
    </div>
  )
}
