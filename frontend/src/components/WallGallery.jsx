/**
 * Centered wall-gallery (1-2-3-2-1).
 * Local photos: public/gallery/01.jpg … 09.jpg
 * When active cases load, frames link to case modal (hover + click).
 */
import { useState } from 'react'
import { formatEventDate } from '../lib/caseHelpers.js'

const SLOTS = [
  { id: '01', orient: 'portrait', src: '/gallery/01.jpg' },
  { id: '02', orient: 'portrait', src: '/gallery/02.jpg' },
  { id: '03', orient: 'portrait', src: '/gallery/03.jpg' },
  { id: '04', orient: 'landscape', src: '/gallery/04.jpg' },
  { id: '05', orient: 'landscape', src: '/gallery/05.jpg' },
  { id: '06', orient: 'landscape', src: '/gallery/06.jpg' },
  { id: '07', orient: 'portrait', src: '/gallery/07.jpg' },
  { id: '08', orient: 'portrait', src: '/gallery/08.jpg' },
  { id: '09', orient: 'portrait', src: '/gallery/09.jpg' },
]

function Frame({ slot, person, index, onSelect }) {
  const [localFailed, setLocalFailed] = useState(false)
  const [caseFailed, setCaseFailed] = useState(false)
  const orientClass =
    slot.orient === 'landscape' ? 'wall-frame-landscape' : 'wall-frame-portrait'

  const casePhoto = person?.photo_url && !caseFailed ? person.photo_url : null
  const localPhoto = !localFailed ? slot.src : null
  const src = casePhoto || localPhoto
  const interactive = Boolean(person)

  return (
    <button
      type="button"
      className={`wall-frame wall-frame-interactive ${orientClass}`}
      style={{ animationDelay: `${80 + index * 70}ms` }}
      aria-label={
        person
          ? `View case for ${person.name}`
          : `Gallery frame ${slot.id}`
      }
      onClick={() => onSelect?.({ person, gallerySrc: src || slot.src, slotId: slot.id })}
    >
      {src ? (
        <img
          src={src}
          alt={person?.name || ''}
          loading="lazy"
          onError={() => {
            if (casePhoto) setCaseFailed(true)
            else setLocalFailed(true)
          }}
        />
      ) : (
        <div className="wall-frame-empty">
          Add
          <br />
          {slot.id}.jpg
        </div>
      )}

      <div className="wall-frame-overlay">
        {person ? (
          <>
            <p className="wall-frame-name">{person.name}</p>
            <p className="wall-frame-meta">
              {person.last_seen_location}
              {person.last_seen_date
                ? ` · ${formatEventDate(person.last_seen_date) || person.last_seen_date}`
                : ''}
            </p>
            <p className="wall-frame-cta">View case →</p>
          </>
        ) : (
          <p className="wall-frame-cta">Search Lookup →</p>
        )}
      </div>

      {interactive && (
        <span className="wall-frame-dot" aria-hidden title="Active case" />
      )}
    </button>
  )
}

export default function WallGallery({ persons = [], onSelect }) {
  const frames = SLOTS.map((slot, i) => ({
    slot,
    person: persons[i] || null,
    index: i,
  }))

  const cols = [
    [frames[0]],
    [frames[1], frames[2]],
    [frames[3], frames[4], frames[5]],
    [frames[6], frames[7]],
    [frames[8]],
  ]

  return (
    <div className="wall-gallery" aria-label="Photo gallery wall">
      {cols.map((col, i) => (
        <div key={i} className={`wall-col ${i === 2 ? 'wall-col-center' : ''}`}>
          {col.map(({ slot, person, index }) => (
            <Frame
              key={slot.id}
              slot={slot}
              person={person}
              index={index}
              onSelect={onSelect}
            />
          ))}
        </div>
      ))}
    </div>
  )
}

export { SLOTS as GALLERY_SLOTS }
