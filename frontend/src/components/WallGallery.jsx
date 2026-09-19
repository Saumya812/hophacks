/**
 * Centered wall-gallery layout (1-2-3-2-1 frames).
 * Drop photos into frontend/public/gallery/ as 01.jpg … 09.jpg
 */
import { useState } from 'react'

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

function Frame({ slot, label }) {
  const [failed, setFailed] = useState(false)
  const orientClass =
    slot.orient === 'landscape' ? 'wall-frame-landscape' : 'wall-frame-portrait'

  return (
    <div className={`wall-frame ${orientClass}`} aria-label={label}>
      {!failed ? (
        <img src={slot.src} alt="" loading="lazy" onError={() => setFailed(true)} />
      ) : (
        <div className="wall-frame-empty">
          Add
          <br />
          {slot.id}.jpg
        </div>
      )}
    </div>
  )
}

export default function WallGallery() {
  const cols = [
    [SLOTS[0]],
    [SLOTS[1], SLOTS[2]],
    [SLOTS[3], SLOTS[4], SLOTS[5]],
    [SLOTS[6], SLOTS[7]],
    [SLOTS[8]],
  ]

  return (
    <div className="wall-gallery" role="img" aria-label="Photo gallery wall">
      {cols.map((frames, i) => (
        <div
          key={i}
          className={`wall-col ${i === 2 ? 'wall-col-center' : ''}`}
        >
          {frames.map((slot) => (
            <Frame key={slot.id} slot={slot} label={`Gallery photo ${slot.id}`} />
          ))}
        </div>
      ))}
    </div>
  )
}
