/**
 * /report — form to create a missing-person profile.
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createPerson } from '../api.js'

const empty = {
  name: '',
  age: '',
  gender: '',
  last_seen_location: '',
  last_seen_date: '',
  description: '',
  photo_url: '',
  police_report_number: '',
  status: 'active',
}

export default function Report() {
  const navigate = useNavigate()
  const [form, setForm] = useState(empty)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  function update(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSubmitting(true)
    setError('')
    try {
      const payload = {
        name: form.name.trim(),
        age: Number(form.age),
        gender: form.gender.trim() || null,
        last_seen_location: form.last_seen_location.trim(),
        last_seen_date: form.last_seen_date,
        description: form.description.trim(),
        photo_url: form.photo_url.trim() || null,
        police_report_number: form.police_report_number.trim() || null,
        status: 'active',
      }
      const created = await createPerson(payload)
      navigate(`/person/${created.id}`)
    } catch (err) {
      setError(err.message || 'Could not create profile')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <div>
        <h1 className="font-display text-3xl text-navy sm:text-4xl">Report a missing person</h1>
        <p className="mt-2 text-navy/70">
          Create a public case profile. Anyone can later submit tips on the case page.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4 border border-navy/10 bg-white/80 p-4 sm:p-6">
        <div>
          <label className="label-field" htmlFor="name">Full name *</label>
          <input
            id="name"
            className="input-field"
            required
            value={form.name}
            onChange={(e) => update('name', e.target.value)}
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label-field" htmlFor="age">Age *</label>
            <input
              id="age"
              type="number"
              min="0"
              max="150"
              className="input-field"
              required
              value={form.age}
              onChange={(e) => update('age', e.target.value)}
            />
          </div>
          <div>
            <label className="label-field" htmlFor="gender">Gender</label>
            <input
              id="gender"
              className="input-field"
              value={form.gender}
              onChange={(e) => update('gender', e.target.value)}
            />
          </div>
        </div>

        <div>
          <label className="label-field" htmlFor="last_seen_location">Last seen location *</label>
          <input
            id="last_seen_location"
            className="input-field"
            required
            placeholder="City, neighborhood, or address"
            value={form.last_seen_location}
            onChange={(e) => update('last_seen_location', e.target.value)}
          />
        </div>

        <div>
          <label className="label-field" htmlFor="last_seen_date">Last seen date *</label>
          <input
            id="last_seen_date"
            type="date"
            className="input-field"
            required
            value={form.last_seen_date}
            onChange={(e) => update('last_seen_date', e.target.value)}
          />
        </div>

        <div>
          <label className="label-field" htmlFor="description">Description *</label>
          <textarea
            id="description"
            className="input-field min-h-[120px]"
            required
            placeholder="Appearance, clothing, circumstances…"
            value={form.description}
            onChange={(e) => update('description', e.target.value)}
          />
        </div>

        <div>
          <label className="label-field" htmlFor="photo_url">Photo URL</label>
          <input
            id="photo_url"
            type="url"
            className="input-field"
            placeholder="https://…"
            value={form.photo_url}
            onChange={(e) => update('photo_url', e.target.value)}
          />
        </div>

        <div>
          <label className="label-field" htmlFor="police_report_number">Police report number</label>
          <input
            id="police_report_number"
            className="input-field"
            value={form.police_report_number}
            onChange={(e) => update('police_report_number', e.target.value)}
          />
        </div>

        {error && (
          <p className="border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p>
        )}

        <button type="submit" className="btn-primary w-full sm:w-auto" disabled={submitting}>
          {submitting ? 'Creating…' : 'Create profile'}
        </button>
      </form>
    </div>
  )
}
