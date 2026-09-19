/**
 * Homepage panel — upload a face photo and match against active cases.
 */
import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { matchFace } from '../api.js'

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

export default function FaceMatchPanel() {
  const [photo, setPhoto] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const inputRef = useRef(null)

  async function onFile(file) {
    if (!file) return
    if (!file.type.startsWith('image/')) {
      setError('Upload a JPG or PNG photo.')
      return
    }
    setError('')
    setResult(null)
    setPhoto(await fileToDataUrl(file))
  }

  async function runMatch() {
    if (!photo) {
      setError('Choose a clear face photo first.')
      return
    }
    setBusy(true)
    setError('')
    try {
      const data = await matchFace({ photo, min_similarity: 55 })
      setResult(data)
    } catch (err) {
      setError(err.message || 'Face match failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="surface-card p-5 sm:p-6">
      <div className="mb-4">
        <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-text-muted">
          Face recognition
        </p>
        <h2 className="font-display text-2xl text-navy">Match a photo to active cases</h2>
        <p className="mt-1 text-sm text-text-muted">
          Upload a clear, front-facing photo. We compare it to profile photos on active cases
          and show similarity scores. Assistive match only — not proof of identity.
        </p>
      </div>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
        <button
          type="button"
          className="flex h-36 w-full shrink-0 flex-col items-center justify-center border border-dashed border-navy/25 bg-white text-sm text-navy/60 hover:border-navy/50 sm:w-36"
          onClick={() => inputRef.current?.click()}
        >
          {photo ? (
            <img src={photo} alt="Probe" className="h-full w-full object-cover" />
          ) : (
            <span>Drop / choose photo</span>
          )}
        </button>
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(e) => onFile(e.target.files?.[0])}
        />
        <div className="flex-1 space-y-3">
          <button type="button" className="btn-primary" disabled={busy} onClick={runMatch}>
            {busy ? 'Comparing…' : 'Find matching cases'}
          </button>
          {error && (
            <p className="border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p>
          )}
          {result?.unavailable && (
            <p className="border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
              {result.message}
            </p>
          )}
          {result && !result.unavailable && (
            <div className="space-y-3">
              <p className="font-display text-xl text-navy">{result.message}</p>
              <p className="text-xs text-navy/50">
                Engine: {result.engine || 'n/a'} · scanned {result.candidates_scanned} photos
              </p>
              <ul className="space-y-2">
                {(result.matches || []).map((m) => (
                  <li
                    key={m.person_id}
                    className="flex items-center gap-3 border border-navy/10 bg-white px-3 py-2"
                  >
                    <div className="h-12 w-10 overflow-hidden bg-navy-100">
                      {m.photo_url ? (
                        <img src={m.photo_url} alt="" className="h-full w-full object-cover" />
                      ) : null}
                    </div>
                    <div className="min-w-0 flex-1">
                      <Link
                        to={`/person/${m.person_id}`}
                        className="font-semibold text-navy underline-offset-2 hover:underline"
                      >
                        {m.name}
                      </Link>
                      <p className="text-xs text-navy/55">{m.last_seen_location}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-display text-lg text-navy">{m.similarity}%</p>
                      <p className="text-[10px] uppercase tracking-wide text-navy/45">similarity</p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
