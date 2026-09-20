/**
 * Hologram wall gallery — 5-column diamond wall
 * (2 portrait | 3 portrait | 4 landscape | 3 portrait | 2 portrait)
 * with glass / glow hologram styling.
 */
import { useCallback, useRef, useState } from 'react'
import { formatEventDate } from '../lib/caseHelpers.js'

const MAX_FRAMES = 14

/** Slot definitions for the diamond wall (index = wall position). */
const SLOTS = [
  { orient: 'portrait' }, // 0 outer-left
  { orient: 'portrait' }, // 1 outer-left
  { orient: 'portrait' }, // 2 mid-left
  { orient: 'portrait' }, // 3 mid-left
  { orient: 'portrait' }, // 4 mid-left
  { orient: 'landscape' }, // 5 center
  { orient: 'landscape' }, // 6 center
  { orient: 'landscape' }, // 7 center
  { orient: 'landscape' }, // 8 center
  { orient: 'portrait' }, // 9 mid-right
  { orient: 'portrait' }, // 10 mid-right
  { orient: 'portrait' }, // 11 mid-right
  { orient: 'portrait' }, // 12 outer-right
  { orient: 'portrait' }, // 13 outer-right
]

/** Fill center first, then flanking columns, then outers. */
const FILL_ORDER = [5, 6, 7, 8, 2, 3, 4, 9, 10, 11, 0, 1, 12, 13]

const COLUMNS = [
  { kind: 'outer', slots: [0, 1] },
  { kind: 'mid', slots: [2, 3, 4] },
  { kind: 'center', slots: [5, 6, 7, 8] },
  { kind: 'mid', slots: [9, 10, 11] },
  { kind: 'outer', slots: [12, 13] },
]

function Frame({ person, orient, index, onSelect }) {
  const [failed, setFailed] = useState(false)
  const src = !failed && person?.photo_url ? person.photo_url : null

  return (
    <button
      type="button"
      className={`holo-frame holo-frame-${orient}`}
      style={{ animationDelay: `${index * 0.18}s` }}
      aria-label={`View case for ${person.name}`}
      onClick={() => onSelect?.({ person, gallerySrc: src, slotId: person.id })}
    >
      <span className="holo-frame-glass">
        {src ? (
          <img
            src={src}
            alt={person.name || ''}
            loading="lazy"
            onError={() => setFailed(true)}
          />
        ) : (
          <span className="holo-frame-empty">?</span>
        )}
        <span className="holo-frame-overlay">
          <span className="holo-frame-name">{person.name}</span>
          <span className="holo-frame-meta">
            {person.last_seen_location}
            {person.last_seen_date
              ? ` · ${formatEventDate(person.last_seen_date) || person.last_seen_date}`
              : ''}
          </span>
          <span className="holo-frame-cta">View case →</span>
        </span>
        <span className="holo-frame-dot" title="Active case" aria-hidden />
      </span>
    </button>
  )
}

export default function WallGallery({ persons = [], onSelect }) {
  const stageRef = useRef(null)
  const withPhotos = (persons || [])
    .filter((p) => Boolean(p?.photo_url))
    .slice(0, MAX_FRAMES)

  const onMove = useCallback((e) => {
    const el = stageRef.current
    if (!el) return
    const r = el.getBoundingClientRect()
    const px = (e.clientX - r.left) / r.width - 0.5
    const py = (e.clientY - r.top) / r.height - 0.5
    el.style.setProperty('--parx', `${px * 8}deg`)
    el.style.setProperty('--pary', `${-py * 5}deg`)
  }, [])

  const onLeave = useCallback(() => {
    const el = stageRef.current
    if (!el) return
    el.style.setProperty('--parx', '0deg')
    el.style.setProperty('--pary', '0deg')
  }, [])

  if (withPhotos.length === 0) {
    return (
      <div className="holo-stage holo-stage-empty" aria-label="Photo gallery">
        <p className="text-sm text-text-muted">
          Cases with photos will appear here as floating frames.
        </p>
      </div>
    )
  }

  const assigned = Array(MAX_FRAMES).fill(null)
  withPhotos.forEach((p, i) => {
    assigned[FILL_ORDER[i]] = p
  })

  return (
    <div
      ref={stageRef}
      className="holo-stage"
      aria-label="Hologram photo gallery"
      onMouseMove={onMove}
      onMouseLeave={onLeave}
    >
      <div className="holo-field holo-wall">
        {COLUMNS.map((col, ci) => {
          const items = col.slots
            .map((slotIndex) => ({
              slotIndex,
              person: assigned[slotIndex],
              orient: SLOTS[slotIndex].orient,
            }))
            .filter((row) => row.person)

          if (items.length === 0) return null

          return (
            <div key={`col-${ci}`} className={`holo-col holo-col-${col.kind}`}>
              {items.map((item) => (
                <Frame
                  key={item.person.id}
                  person={item.person}
                  orient={item.orient}
                  index={item.slotIndex}
                  onSelect={onSelect}
                />
              ))}
            </div>
          )
        })}
      </div>
    </div>
  )
}
