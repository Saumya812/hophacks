/**
 * /report — compassionate missing-person report form.
 */
import { useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { checkDuplicates, createPerson } from '../api.js'

const empty = {
  name: '',
  age: '',
  gender: '',
  last_seen_location: '',
  last_seen_date: '',
  last_seen_time: '',
  description: '',
  photo_url: '',
  contact_email: '',
  police_report_number: '',
  status: 'active',
}

const DESC_MAX = 5000

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

function UploadIcon() {
  return (
    <svg width="36" height="36" viewBox="0 0 24 24" fill="none" aria-hidden className="text-navy">
      <path
        d="M12 16V4m0 0l-4 4m4-4l4 4M4 16.5V18a2 2 0 002 2h12a2 2 0 002-2v-1.5"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function PinIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden
      className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-text-muted"
    >
      <path
        d="M12 21s7-5.4 7-11a7 7 0 10-14 0c0 5.6 7 11 7 11z"
        stroke="currentColor"
        strokeWidth="1.75"
      />
      <circle cx="12" cy="10" r="2.5" stroke="currentColor" strokeWidth="1.75" />
    </svg>
  )
}

export default function Report() {
  const navigate = useNavigate()
  const fileRef = useRef(null)
  const [form, setForm] = useState(empty)
  const [photoName, setPhotoName] = useState('')
  const [dragOver, setDragOver] = useState(false)
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

  function clearPhoto() {
    update('photo_url', '')
    setPhotoName('')
    if (fileRef.current) fileRef.current.value = ''
  }

  async function create() {
    const payload = {
      name: form.name.trim(),
      age: Number(form.age),
      gender: form.gender.trim() || null,
      last_seen_location: form.last_seen_location.trim(),
      last_seen_date: form.last_seen_date,
      last_seen_time: form.last_seen_time.trim() || null,
      description: form.description.trim(),
      photo_url: form.photo_url.trim() || null,
      police_report_number: form.police_report_number.trim() || null,
      contact_email: form.contact_email.trim() || null,
      status: 'active',
    }
    const created = await createPerson(payload)
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
    <div className="bg-cream pb-20 pt-10">
      <div className="mx-auto max-w-[680px] px-4 sm:px-6">
        <form onSubmit={handleSubmit} className="surface-card overflow-hidden">
          <div className="bg-navy px-6 py-7 text-white sm:px-8">
            <h1 className="font-display text-3xl sm:text-4xl">Report a missing person</h1>
            <p className="mt-2 text-sm text-white/65 sm:text-base">
              This profile will be visible to the public. Please provide as much detail as
              possible.
            </p>
          </div>

          <div className="space-y-0 px-6 py-2 sm:px-8">
            {/* Section 1 */}
            <section className="border-b border-border py-8">
              <h2 className="font-display text-xl text-navy">Basic information</h2>
              <div className="mt-5 space-y-4">
                <div>
                  <label className="label-field" htmlFor="name">
                    Full name *
                  </label>
                  <input
                    id="name"
                    className="input-field min-h-12"
                    required
                    value={form.name}
                    onChange={(e) => update('name', e.target.value)}
                  />
                  <p className="helper-text">Legal or commonly used name</p>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label className="label-field" htmlFor="age">
                      Age *
                    </label>
                    <input
                      id="age"
                      type="number"
                      min="0"
                      max="150"
                      className="input-field min-h-12"
                      required
                      value={form.age}
                      onChange={(e) => update('age', e.target.value)}
                    />
                    <p className="helper-text">Approximate age is fine</p>
                  </div>
                  <div>
                    <label className="label-field" htmlFor="gender">
                      Gender
                    </label>
                    <input
                      id="gender"
                      className="input-field min-h-12"
                      value={form.gender}
                      onChange={(e) => update('gender', e.target.value)}
                    />
                    <p className="helper-text">Optional</p>
                  </div>
                </div>
              </div>
            </section>

            {/* Section 2 */}
            <section className="border-b border-border py-8">
              <h2 className="font-display text-xl text-navy">Last known location</h2>
              <div className="mt-5 space-y-4">
                <div>
                  <label className="label-field" htmlFor="last_seen_location">
                    Last seen location *
                  </label>
                  <div className="relative">
                    <PinIcon />
                    <input
                      id="last_seen_location"
                      className="input-field min-h-12 pl-10"
                      required
                      placeholder="City, neighborhood, or address"
                      value={form.last_seen_location}
                      onChange={(e) => update('last_seen_location', e.target.value)}
                    />
                  </div>
                  <p className="helper-text">
                    Be as specific as possible — street, neighborhood, or landmark
                  </p>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label className="label-field" htmlFor="last_seen_date">
                      Last seen date *
                    </label>
                    <input
                      id="last_seen_date"
                      type="date"
                      className="input-field min-h-12"
                      required
                      value={form.last_seen_date}
                      onChange={(e) => update('last_seen_date', e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="label-field" htmlFor="last_seen_time">
                      Approximate time
                    </label>
                    <input
                      id="last_seen_time"
                      type="time"
                      className="input-field min-h-12"
                      value={form.last_seen_time}
                      onChange={(e) => update('last_seen_time', e.target.value)}
                    />
                    <p className="helper-text">Optional approximate time</p>
                  </div>
                </div>
              </div>
            </section>

            {/* Section 3 */}
            <section className="border-b border-border py-8">
              <h2 className="font-display text-xl text-navy">Description</h2>
              <div className="mt-5">
                <label className="label-field" htmlFor="description">
                  Appearance & circumstances *
                </label>
                <div className="relative">
                  <textarea
                    id="description"
                    className="input-field h-[140px] resize-y"
                    required
                    maxLength={DESC_MAX}
                    placeholder="Appearance, clothing, distinguishing features..."
                    value={form.description}
                    onChange={(e) => update('description', e.target.value)}
                  />
                  <span className="pointer-events-none absolute bottom-3 right-3 text-xs text-text-muted">
                    {form.description.length}/{DESC_MAX}
                  </span>
                </div>
              </div>
            </section>

            {/* Section 4 */}
            <section className="border-b border-border py-8">
              <h2 className="font-display text-xl text-navy">Photo</h2>
              <div className="mt-5">
                {form.photo_url ? (
                  <div className="flex flex-wrap items-center gap-4 rounded-xl border border-border bg-cream p-4">
                    <img
                      src={form.photo_url}
                      alt="Preview"
                      className="h-24 w-24 rounded-lg object-cover"
                    />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold text-navy">
                        {photoName || 'Photo ready'}
                      </p>
                      <p className="helper-text">Clear, recent, front-facing photo preferred</p>
                      <button
                        type="button"
                        className="mt-2 text-sm font-semibold text-danger underline"
                        onClick={clearPhoto}
                      >
                        Remove photo
                      </button>
                    </div>
                  </div>
                ) : (
                  <div
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') fileRef.current?.click()
                    }}
                    onClick={() => fileRef.current?.click()}
                    onDragOver={(e) => {
                      e.preventDefault()
                      setDragOver(true)
                    }}
                    onDragLeave={() => setDragOver(false)}
                    onDrop={(e) => {
                      e.preventDefault()
                      setDragOver(false)
                      onPhotoFile(e.dataTransfer.files?.[0])
                    }}
                    className={`drop-zone ${dragOver ? 'drop-zone-active' : ''}`}
                  >
                    <UploadIcon />
                    <p className="mt-3 text-sm font-semibold text-navy">
                      Drag photo here or click to browse
                    </p>
                    <p className="mt-1 text-xs text-text-muted">
                      Clear, recent, front-facing photo preferred
                    </p>
                  </div>
                )}
                <input
                  ref={fileRef}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={(e) => onPhotoFile(e.target.files?.[0])}
                />
                <input
                  id="photo_url"
                  className="input-field mt-3 min-h-12"
                  placeholder="Or paste https://… image URL"
                  value={form.photo_url.startsWith('data:') ? '' : form.photo_url}
                  onChange={(e) => {
                    setPhotoName('')
                    update('photo_url', e.target.value)
                  }}
                />
              </div>
            </section>

            {/* Section 5 */}
            <section className="py-8">
              <h2 className="font-display text-xl text-navy">Contact</h2>
              <div className="mt-5 space-y-4">
                <div>
                  <label className="label-field" htmlFor="contact_email">
                    Your email
                  </label>
                  <input
                    id="contact_email"
                    type="email"
                    className="input-field min-h-12"
                    placeholder="for case updates"
                    value={form.contact_email}
                    onChange={(e) => update('contact_email', e.target.value)}
                  />
                  <p className="helper-text">
                    Optional. We save it as the case watcher for updates (logged on the server; not
                    shown on the public profile).
                  </p>
                </div>
                <div>
                  <label className="label-field" htmlFor="police_report_number">
                    Police report number
                  </label>
                  <input
                    id="police_report_number"
                    className="input-field min-h-12"
                    value={form.police_report_number}
                    onChange={(e) => update('police_report_number', e.target.value)}
                  />
                  <p className="helper-text">
                    If you add a report number, this profile is marked Verified when it is published.
                  </p>
                </div>
              </div>
            </section>

            {dupes?.possible_duplicate && (
              <div className="mb-6 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950">
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
              <p className="mb-6 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
                {error}
              </p>
            )}

            <div className="pb-8">
              <button
                type="submit"
                className="btn-primary h-14 w-full text-base"
                disabled={submitting || checking}
              >
                {checking
                  ? 'Checking duplicates…'
                  : submitting
                    ? 'Publishing…'
                    : forceCreate
                      ? 'Publish anyway'
                      : 'Publish case profile'}
              </button>
              <p className="mt-3 text-center text-xs text-text-muted">
                False reports may have legal consequences. This platform must not be misused.
              </p>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}
