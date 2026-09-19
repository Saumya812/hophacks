/**
 * Tip submission on person profile — posts to existing /persons/:id/sightings.
 * Maps UI confidence to API 1–5 integers. Does not replace /tip/:id.
 */
import { useMemo, useState } from 'react'
import { createSighting } from '../api.js'
import { showToast } from './Toast.jsx'

const TIP_TYPES = [
  { id: 'saw_person', label: 'I saw this person', icon: '👁' },
  { id: 'know_location', label: 'I know their location', icon: '📍' },
  { id: 'have_info', label: 'I have information', icon: 'ℹ️' },
  { id: 'unsure', label: "I'm not sure but…", icon: '❓' },
]

const CONFIDENCE = [
  { id: 'high', label: "Certain — I'm sure it was them", api: 5 },
  { id: 'medium', label: 'Likely — I think it was them', api: 3 },
  { id: 'low', label: 'Unsure — might be worth checking', api: 2 },
]

const empty = {
  tip_type: '',
  location_text: '',
  lat: null,
  lng: null,
  date: '',
  time: '',
  description: '',
  confidence: 'medium',
  email: '',
  consent: false,
}

async function geocodeText(query) {
  const q = (query || '').trim()
  if (!q) return null
  const url = `https://nominatim.openstreetmap.org/search?format=json&limit=1&q=${encodeURIComponent(q)}`
  const res = await fetch(url, {
    headers: { Accept: 'application/json', 'User-Agent': 'FindMyPal/1.0' },
  })
  if (!res.ok) return null
  const data = await res.json()
  if (!data?.[0]) return null
  return { lat: Number(data[0].lat), lng: Number(data[0].lon) }
}

export default function TipForm({ personId, personName, onSubmitted }) {
  const [form, setForm] = useState(empty)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [geoMsg, setGeoMsg] = useState('')
  const [done, setDone] = useState(false)

  const chars = form.description.length
  const canSubmit = useMemo(() => {
    return (
      form.tip_type &&
      form.location_text.trim().length >= 2 &&
      form.date &&
      form.time &&
      form.description.trim().length >= 20 &&
      form.confidence
    )
  }, [form])

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
        update('lat', pos.coords.latitude)
        update('lng', pos.coords.longitude)
        setGeoMsg('Location captured ✓')
      },
      () => setGeoMsg('Could not read your location. Enter a place name instead.'),
      { enableHighAccuracy: true, timeout: 12000 },
    )
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!canSubmit || submitting) return
    setSubmitting(true)
    setError('')
    try {
      let lat = form.lat
      let lng = form.lng
      if (lat == null || lng == null) {
        const geo = await geocodeText(form.location_text)
        if (!geo) {
          throw new Error(
            'Could not place that location on the map. Try “Use my current location” or a clearer place name.',
          )
        }
        lat = geo.lat
        lng = geo.lng
      }

      const conf = CONFIDENCE.find((c) => c.id === form.confidence) || CONFIDENCE[1]
      const tipLabel = TIP_TYPES.find((t) => t.id === form.tip_type)?.label || form.tip_type
      const iso = new Date(`${form.date}T${form.time}`).toISOString()
      const description = `[${tipLabel}] ${form.description.trim()}\nPlace: ${form.location_text.trim()}`

      await createSighting(personId, {
        location_lat: Number(lat),
        location_lng: Number(lng),
        date_time: iso,
        description,
        confidence_level: conf.api,
        submitter_email:
          form.consent && form.email.trim() ? form.email.trim() : null,
        tip_type: form.tip_type,
      })

      setDone(true)
      showToast('Tip submitted — case updated', 'success')
      onSubmitted?.()
    } catch (err) {
      setError(err.message || 'Could not submit tip')
      showToast(err.message || 'Could not submit tip', 'warning')
    } finally {
      setSubmitting(false)
    }
  }

  function reset() {
    setForm(empty)
    setGeoMsg('')
    setError('')
    setDone(false)
  }

  async function shareCase() {
    const url = window.location.href
    try {
      await navigator.clipboard.writeText(url)
      showToast('Case link copied', 'success')
    } catch {
      showToast('Could not copy link', 'warning')
    }
  }

  if (done) {
    return (
      <section className="surface-card border-l-4 border-l-gold p-6 text-center sm:p-8">
        <div
          className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 text-3xl text-emerald-600"
          style={{ animation: 'tip-success-pop 0.45s ease-out both' }}
          aria-hidden
        >
          ✓
        </div>
        <h3 className="font-display text-2xl text-navy">Tip submitted</h3>
        <p className="mx-auto mt-3 max-w-md text-sm leading-relaxed text-text-muted">
          Your tip has been recorded and local authorities have been notified. Thank you for helping
          bring {personName || 'them'} home.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <button type="button" className="btn-primary" onClick={reset}>
            Submit another tip
          </button>
          <button type="button" className="btn-secondary" onClick={shareCase}>
            Share this case
          </button>
        </div>
      </section>
    )
  }

  return (
    <section className="surface-card border-l-4 border-l-gold p-5 sm:p-6">
      <h3 className="font-display text-2xl text-navy">Submit a Tip</h3>
      <p className="mt-2 text-sm text-text-muted" style={{ fontFamily: 'Inter, system-ui' }}>
        Did you see this person? Share what you know. Tips are community-provided and
        unverified.
      </p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-6">
        <fieldset>
          <legend className="label-field">What did you see? *</legend>
          <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
            {TIP_TYPES.map((t) => {
              const selected = form.tip_type === t.id
              return (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => update('tip_type', t.id)}
                  className={`min-h-[52px] rounded-lg border px-3 py-3 text-left text-sm font-medium transition-colors ${
                    selected
                      ? 'border-navy bg-navy text-white'
                      : 'border-navy/40 bg-white text-navy hover:bg-stone/50'
                  }`}
                >
                  <span className="mr-2" aria-hidden>
                    {t.icon}
                  </span>
                  {t.label}
                </button>
              )
            })}
          </div>
        </fieldset>

        <div>
          <label className="label-field" htmlFor="tip-location">
            Location *
          </label>
          <input
            id="tip-location"
            className="input-field mt-1"
            placeholder="Street, neighborhood, landmark, or city"
            value={form.location_text}
            onChange={(e) => update('location_text', e.target.value)}
            required
          />
          <button
            type="button"
            onClick={useMyLocation}
            className="mt-2 text-sm font-semibold text-navy underline"
          >
            Or use my current location
          </button>
          {geoMsg && (
            <p
              className={`mt-1 text-sm ${
                geoMsg.includes('✓') ? 'text-emerald-700' : 'text-text-muted'
              }`}
            >
              {geoMsg}
            </p>
          )}
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label-field" htmlFor="tip-date">
              When — date *
            </label>
            <input
              id="tip-date"
              type="date"
              className="input-field mt-1"
              value={form.date}
              onChange={(e) => update('date', e.target.value)}
              required
            />
          </div>
          <div>
            <label className="label-field" htmlFor="tip-time">
              When — time *
            </label>
            <input
              id="tip-time"
              type="time"
              className="input-field mt-1"
              value={form.time}
              onChange={(e) => update('time', e.target.value)}
              required
            />
          </div>
        </div>

        <div>
          <label className="label-field" htmlFor="tip-desc">
            Description *
          </label>
          <div className="relative mt-1">
            <textarea
              id="tip-desc"
              className="input-field min-h-[120px] resize-y pb-8"
              placeholder="Describe what you saw — clothing, direction they were heading, who they were with…"
              value={form.description}
              onChange={(e) => update('description', e.target.value)}
              required
              minLength={20}
            />
            <span className="pointer-events-none absolute bottom-2 right-3 text-xs text-text-muted">
              {chars}/20 min
            </span>
          </div>
        </div>

        <fieldset>
          <legend className="label-field">Confidence level</legend>
          <div className="mt-2 flex flex-wrap gap-2">
            {CONFIDENCE.map((c) => {
              const selected = form.confidence === c.id
              return (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => update('confidence', c.id)}
                  className={`rounded-full border px-3 py-2 text-left text-xs font-medium sm:text-sm ${
                    selected
                      ? 'border-navy bg-navy text-white'
                      : 'border-border bg-white text-navy hover:bg-stone/40'
                  }`}
                >
                  {c.label}
                </button>
              )
            })}
          </div>
        </fieldset>

        <div>
          <label className="label-field" htmlFor="tip-email">
            Your contact (optional)
          </label>
          <input
            id="tip-email"
            type="email"
            className="input-field mt-1"
            placeholder="Only shared with authorities if needed"
            value={form.email}
            onChange={(e) => update('email', e.target.value)}
          />
          <label className="mt-3 flex items-start gap-2 text-sm text-text-muted">
            <input
              type="checkbox"
              className="mt-1"
              checked={form.consent}
              onChange={(e) => update('consent', e.target.checked)}
            />
            <span>I consent to being contacted by police about this tip</span>
          </label>
        </div>

        {error && (
          <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={!canSubmit || submitting}
          className="btn-primary h-14 w-full text-base"
        >
          {submitting ? 'Submitting…' : 'Submit tip'}
        </button>
      </form>
    </section>
  )
}
