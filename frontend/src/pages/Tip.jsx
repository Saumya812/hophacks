/**
 * /tip/:id — public tip / sighting submission form.
 */
import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { createSighting, getPerson } from '../api.js'

const empty = {
  location_lat: '',
  location_lng: '',
  date_time: '',
  description: '',
  confidence_level: '3',
  submitter_email: '',
}

export default function Tip() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [person, setPerson] = useState(null)
  const [form, setForm] = useState(empty)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [geoMsg, setGeoMsg] = useState('')

  useEffect(() => {
    let cancelled = false
    getPerson(id)
      .then((p) => {
        if (!cancelled) setPerson(p)
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'Case not found')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [id])

  function update(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  function useMyLocation() {
    setGeoMsg('')
    if (!navigator.geolocation) {
      setGeoMsg('Geolocation is not supported in this browser.')
      return
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        update('location_lat', pos.coords.latitude.toFixed(6))
        update('location_lng', pos.coords.longitude.toFixed(6))
        setGeoMsg('Location filled from your device.')
      },
      () => setGeoMsg('Could not read your location. Enter lat/lng manually.'),
    )
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSubmitting(true)
    setError('')
    try {
      const iso = form.date_time ? new Date(form.date_time).toISOString() : null
      const payload = {
        location_lat: Number(form.location_lat),
        location_lng: Number(form.location_lng),
        date_time: iso,
        description: form.description.trim(),
        confidence_level: Number(form.confidence_level),
        submitter_email: form.submitter_email.trim() || null,
      }
      await createSighting(id, payload)
      navigate(`/person/${id}`)
    } catch (err) {
      setError(err.message || 'Could not submit tip')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return <p className="page-pad text-text-muted">Loading…</p>

  if (!person) {
    return (
      <p className="page-pad rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
        {error || 'Case not found'}
      </p>
    )
  }

  return (
    <div className="bg-cream pb-20 pt-10">
      <div className="mx-auto max-w-xl px-4 sm:px-6">
        <div className="mb-6">
          <p className="text-sm text-text-muted">
            Tip for{' '}
            <Link to={`/person/${person.id}`} className="font-semibold text-navy underline">
              {person.name}
            </Link>
          </p>
          <h1 className="font-display text-3xl text-navy sm:text-4xl">Submit a sighting</h1>
          <p className="mt-2 text-text-muted">
            Share where and when you may have seen this person. Tips appear on the case map and
            timeline.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="surface-card space-y-4 p-5 sm:p-6">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="label-field" htmlFor="location_lat">
                Latitude *
              </label>
              <input
                id="location_lat"
                type="number"
                step="any"
                min="-90"
                max="90"
                className="input-field min-h-12"
                required
                value={form.location_lat}
                onChange={(e) => update('location_lat', e.target.value)}
              />
            </div>
            <div>
              <label className="label-field" htmlFor="location_lng">
                Longitude *
              </label>
              <input
                id="location_lng"
                type="number"
                step="any"
                min="-180"
                max="180"
                className="input-field min-h-12"
                required
                value={form.location_lng}
                onChange={(e) => update('location_lng', e.target.value)}
              />
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button type="button" className="btn-secondary" onClick={useMyLocation}>
              Use my location
            </button>
            {geoMsg && <span className="text-sm text-text-muted">{geoMsg}</span>}
          </div>

          <div>
            <label className="label-field" htmlFor="date_time">
              Date & time *
            </label>
            <input
              id="date_time"
              type="datetime-local"
              className="input-field min-h-12"
              required
              value={form.date_time}
              onChange={(e) => update('date_time', e.target.value)}
            />
          </div>

          <div>
            <label className="label-field" htmlFor="confidence_level">
              Confidence (1 low – 5 high)
            </label>
            <select
              id="confidence_level"
              className="input-field min-h-12"
              value={form.confidence_level}
              onChange={(e) => update('confidence_level', e.target.value)}
            >
              {[1, 2, 3, 4, 5].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="label-field" htmlFor="description">
              What did you see? *
            </label>
            <textarea
              id="description"
              className="input-field min-h-[120px]"
              required
              value={form.description}
              onChange={(e) => update('description', e.target.value)}
            />
          </div>

          <div>
            <label className="label-field" htmlFor="submitter_email">
              Email for follow-up (optional — leave blank to stay anonymous)
            </label>
            <input
              id="submitter_email"
              type="email"
              className="input-field min-h-12"
              value={form.submitter_email}
              onChange={(e) => update('submitter_email', e.target.value)}
            />
            <p className="helper-text">
              Tips can be submitted anonymously. Email is only used if investigators need to follow
              up.
            </p>
          </div>

          {error && (
            <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
              {error}
            </p>
          )}

          <button type="submit" className="btn-primary h-12 w-full" disabled={submitting}>
            {submitting ? 'Submitting…' : 'Submit tip'}
          </button>
        </form>
      </div>
    </div>
  )
}
