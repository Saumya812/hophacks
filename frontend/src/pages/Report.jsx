/**
 * /report — form to create a missing-person profile.
 * Runs duplicate detection (name + optional photo) before create.
 */
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { checkDuplicates, createPerson } from '../api.js'

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

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

export default function Report() {
  const navigate = useNavigate()
  const [form, setForm] = useState(empty)
  const [photoName, setPhotoName] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [checking, setChecking] = useState(false)
  const [error, setError] = useState('')
  const [dupes, setDupes] = useState(null)
  const [forceCreate, setForceCreate] = useState(false)

  function update(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }))
    setDupes(null)
    setForceCreate(false)
  }

  async function onPhotoFile(file) {
    if (!file) return
    if (!file.type.startsWith('image/')) {
      setError('Photo must be an image (JPG or PNG).')
      return
    }
    if (file.size > 4 * 1024 * 1024) {
      setError('Photo must be under 4MB.')
      return
    }
    setError('')
    const dataUrl = await fileToDataUrl(file)
    update('photo_url', dataUrl)
    setPhotoName(file.name)
  }

  async function create() {
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
    // Land on the new case; Cases list refreshes when you click Cases in the nav
    navigate(`/person/${created.id}`, { replace: true })
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSubmitting(true)
    setError('')
    try {
      if (!forceCreate) {
        setChecking(true)
        const screen = await checkDuplicates({
          name: form.name.trim(),
          age: form.age ? Number(form.age) : null,
          photo_url: form.photo_url.trim() || null,
        })
        setChecking(false)
        if (screen.possible_duplicate && (screen.candidates || []).length) {
          setDupes(screen)
          setSubmitting(false)
          return
        }
      }
      await create()
    } catch (err) {
      setError(err.message || 'Could not create profile')
    } finally {
      setChecking(false)
      setSubmitting(false)
    }
  }

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <div>
        <h1 className="font-display text-3xl text-navy sm:text-4xl">Report a missing person</h1>
        <p className="mt-2 text-navy/70">
          Create a public case profile. It will appear under <strong>Cases → Active cases</strong> with
          status active. We screen for possible duplicates before saving.
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
          <label className="label-field" htmlFor="photo_file">Photo (upload or URL)</label>
          <input
            id="photo_file"
            type="file"
            accept="image/*"
            className="input-field"
            onChange={(e) => onPhotoFile(e.target.files?.[0])}
          />
          {photoName && (
            <p className="mt-1 text-xs text-navy/55">Selected: {photoName}</p>
          )}
          <input
            id="photo_url"
            className="input-field mt-2"
            placeholder="Or paste https://… image URL"
            value={form.photo_url.startsWith('data:') ? '' : form.photo_url}
            onChange={(e) => {
              setPhotoName('')
              update('photo_url', e.target.value)
            }}
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

        {dupes?.possible_duplicate && (
          <div className="border border-amber-300 bg-amber-50 px-3 py-3 text-sm text-amber-950">
            <p className="font-semibold">{dupes.message}</p>
            <ul className="mt-2 space-y-2">
              {(dupes.candidates || []).map((c) => (
                <li key={c.person_id} className="flex justify-between gap-2">
                  <Link to={`/person/${c.person_id}`} className="underline">
                    {c.name} (score {c.combined_score})
                  </Link>
                  <span className="text-xs">
                    name {c.name_similarity}%
                    {c.photo_similarity != null ? ` · photo ${c.photo_similarity}%` : ''}
                  </span>
                </li>
              ))}
            </ul>
            <button
              type="button"
              className="btn-secondary mt-3"
              disabled={submitting}
              onClick={async () => {
                setForceCreate(true)
                setDupes(null)
                setSubmitting(true)
                setError('')
                try {
                  await create()
                } catch (err) {
                  setError(err.message || 'Could not create profile')
                } finally {
                  setSubmitting(false)
                }
              }}
            >
              Not a duplicate — create this profile
            </button>
          </div>
        )}

        {error && (
          <p className="border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p>
        )}

        <button type="submit" className="btn-primary w-full sm:w-auto" disabled={submitting || checking}>
          {checking ? 'Checking duplicates…' : submitting ? 'Creating…' : forceCreate ? 'Create anyway' : 'Create profile'}
        </button>
      </form>
    </div>
  )
}
