/**
 * Centered wall gallery — only active cases that have a photo.
 * People without photos are omitted here (they show "?" on their profile).
 */
import { useState } from 'react'
import { formatEventDate } from '../lib/caseHelpers.js'

const MAX_FRAMES = 9
const ORIENTS = [
  'portrait',
  'portrait',
  'portrait',
  'landscape',
  'landscape',
  'landscape',
  'portrait',
  'portrait',
  'portrait',
]

function Frame({ person, orient, index, onSelect }) {
  const [failed, setFailed] = useState(false)
  const orientClass =
    orient === 'landscape' ? 'wall-frame-landscape' : 'wall-frame-portrait'
  const src = !failed && person?.photo_url ? person.photo_url : null

  return (
    <button
      type="button"
      className={`wall-frame wall-frame-interactive ${orientClass}`}
      style={{ animationDelay: `${80 + index * 70}ms` }}
      aria-label={`View case for ${person.name}`}
      onClick={() => onSelect?.({ person, gallerySrc: src, slotId: person.id })}
    >
      {src ? (
        <img
          src={src}
          alt={person.name || ''}
          loading="lazy"
          onError={() => setFailed(true)}
        />
      ) : (
        <div className="wall-frame-empty font-display text-4xl text-ink/30">?</div>
      )}

      <div className="wall-frame-overlay">
        <p className="wall-frame-name">{person.name}</p>
        <p className="wall-frame-meta">
          {person.last_seen_location}
          {person.last_seen_date
            ? ` · ${formatEventDate(person.last_seen_date) || person.last_seen_date}`
            : ''}
        </p>
        <p className="wall-frame-cta">View case →</p>
      </div>

      <span className="wall-frame-dot" aria-hidden title="Active case" />
    </button>
  )
}

/** Pack frames into a balanced 1–2–3–2–1-style column layout. */
function columnPlan(count) {
  if (count <= 0) return []
  if (count === 1) return [1]
  if (count === 2) return [1, 1]
  if (count === 3) return [1, 1, 1]
  if (count === 4) return [1, 2, 1]
  if (count === 5) return [1, 3, 1]
  if (count === 6) return [2, 2, 2]
  if (count === 7) return [2, 3, 2]
  if (count === 8) return [2, 3, 2, 1]
  return [1, 2, 3, 2, 1]
}

export default function WallGallery({ persons = [], onSelect }) {
  const withPhotos = (persons || [])
    .filter((p) => Boolean(p?.photo_url))
    .slice(0, MAX_FRAMES)

  if (withPhotos.length === 0) {
    return (
      <div className="wall-gallery justify-center py-8" aria-label="Photo gallery wall">
        <p className="text-sm text-text-muted">
          Cases with photos will appear here on the wall.
        </p>
      </div>
    )
  }

  const plan = columnPlan(withPhotos.length)
  const frames = withPhotos.map((person, i) => ({
    person,
    orient: ORIENTS[i] || 'portrait',
    index: i,
  }))

  let cursor = 0
  const cols = plan.map((size) => {
    const slice = frames.slice(cursor, cursor + size)
    cursor += size
    return slice
  })

  return (
    <div className="wall-gallery" aria-label="Photo gallery wall">
      {cols.map((col, i) => (
        <div
          key={i}
          className={`wall-col ${cols.length === 5 && i === 2 ? 'wall-col-center' : ''}`}
        >
          {col.map(({ person, orient, index }) => (
            <Frame
              key={person.id}
              person={person}
              orient={orient}
              index={index}
              onSelect={onSelect}
            />
          ))}
        </div>
      ))}
    </div>
  )
}
