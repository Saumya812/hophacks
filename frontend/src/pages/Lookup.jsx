/**
 * /lookup — Smart Person Search (3-step flow). Visual polish only.
 */
import { useEffect, useRef, useState } from 'react'
import { lookupSearch } from '../api.js'
import ReportCard from '../components/ReportCard.jsx'

const STATUS_MESSAGES = [
  'Searching news sources...',
  'Scanning Reddit...',
  'Checking public web...',
  'Running AI extraction...',
  'Compiling your report...',
]

const STEPS = [
  { id: 1, label: 'Input' },
  { id: 2, label: 'Searching' },
  { id: 3, label: 'Report' },
]

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

function Spinner() {
  return <div className="lookup-spinner" aria-hidden />
}

export default function Lookup() {
  const [step, setStep] = useState(1)
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [photoDataUrl, setPhotoDataUrl] = useState(null)
  const [photoName, setPhotoName] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState('')
  const [statusIdx, setStatusIdx] = useState(0)
  const [progress, setProgress] = useState(8)
  const [report, setReport] = useState(null)
  const fileRef = useRef(null)
  const abortRef = useRef(false)

  useEffect(() => {
    if (step !== 2) return undefined
    const statusTimer = setInterval(() => {
      setStatusIdx((i) => (i + 1) % STATUS_MESSAGES.length)
    }, 2000)
    const progTimer = setInterval(() => {
      setProgress((p) => (p >= 92 ? 92 : p + Math.random() * 6))
    }, 700)
    return () => {
      clearInterval(statusTimer)
      clearInterval(progTimer)
    }
  }, [step])

  async function handlePhotoFile(file) {
    if (!file) return
    if (!file.type.startsWith('image/')) {
      setError('Please upload an image file (JPG or PNG).')
      return
    }
    if (file.size > 2.5 * 1024 * 1024) {
      setError('Photo must be under 2.5MB.')
      return
    }
    setError('')
    const dataUrl = await fileToDataUrl(file)
    setPhotoDataUrl(dataUrl)
    setPhotoName(file.name)
  }

  async function handleSearch(e) {
    e.preventDefault()
    const first = firstName.trim()
    const last = lastName.trim()
    if (!first || !last) {
      setError('Enter both first and last name.')
      return
    }
    setError('')
    setReport(null)
    setStep(2)
    setProgress(8)
    setStatusIdx(0)
    abortRef.current = false

    try {
      const data = await lookupSearch({
        name: `${first} ${last}`,
        first_name: first,
        last_name: last,
        photo: photoDataUrl || undefined,
      })
      if (abortRef.current) return
      setProgress(100)
      setReport(data)
      setStep(3)
    } catch (err) {
      if (abortRef.current) return
      setError(err.message || 'Search failed')
      setStep(1)
    }
  }

  function resetAll() {
    abortRef.current = true
    setStep(1)
    setReport(null)
    setError('')
    setProgress(8)
  }

  return (
    <div className="bg-cream pb-20 pt-10">
      <div className="page-pad !pb-0">
        <div className="mb-8 max-w-2xl">
          <p
            className="text-[11px] font-semibold uppercase text-accent"
            style={{ letterSpacing: '3px' }}
          >
            Smart Person Search
          </p>
          <h1 className="mt-2 font-display text-3xl text-navy sm:text-4xl">Person Lookup</h1>
          <p className="mt-2 text-sm leading-relaxed text-text-muted sm:text-base">
            Enter a first and last name. An optional photo enables face match against tip photos
            and public web results you already have access to — not city camera feeds. FindMyPal
            searches publicly indexed sources and compiles a sighting brief. Photos stay in this
            session only.
          </p>
        </div>

        {/* Step indicator */}
        <ol className="mb-10 flex items-center justify-between gap-2">
          {STEPS.map((s, i) => {
            const active = step === s.id
            const done = step > s.id
            const clickable = done
            return (
              <li key={s.id} className="flex flex-1 items-center gap-2">
                <button
                  type="button"
                  disabled={!clickable}
                  onClick={() => {
                    if (clickable) {
                      abortRef.current = true
                      setStep(s.id)
                      if (s.id === 1) setReport(null)
                    }
                  }}
                  className={`flex flex-col items-center gap-2 sm:flex-row sm:gap-3 ${
                    clickable ? 'cursor-pointer' : 'cursor-default'
                  }`}
                >
                  <span
                    className={`flex h-9 w-9 items-center justify-center rounded-md text-sm font-bold transition-all ${
                      active
                        ? 'bg-navy text-white'
                        : done
                          ? 'bg-gold text-white hover:scale-105'
                          : 'bg-border text-text-muted'
                    }`}
                  >
                    {done ? '✓' : s.id}
                  </span>
                  <span
                    className={`text-xs font-semibold sm:text-sm ${
                      active || done ? 'text-navy' : 'text-text-muted'
                    }`}
                  >
                    {s.label}
                  </span>
                </button>
                {i < STEPS.length - 1 && (
                  <div className="mx-1 hidden h-0.5 flex-1 bg-border sm:block" />
                )}
              </li>
            )
          })}
        </ol>

        {/* STEP 1 */}
        {step === 1 && (
          <form
            onSubmit={handleSearch}
            className="surface-card mx-auto max-w-[680px] space-y-6 p-8 sm:p-10 fade-up"
          >
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="label-field" htmlFor="firstName">
                  First name
                </label>
                <input
                  id="firstName"
                  className="input-field min-h-12"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  required
                  autoComplete="given-name"
                />
              </div>
              <div>
                <label className="label-field" htmlFor="lastName">
                  Last name
                </label>
                <input
                  id="lastName"
                  className="input-field min-h-12"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  required
                  autoComplete="family-name"
                />
              </div>
            </div>

            <div>
              <p className="label-field">Photo</p>
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
                  handlePhotoFile(e.dataTransfer.files?.[0])
                }}
                className={`drop-zone ${dragOver ? 'drop-zone-active' : ''}`}
              >
                {photoDataUrl ? (
                  <div className="relative">
                    <img
                      src={photoDataUrl}
                      alt="Upload preview"
                      className="h-20 w-20 rounded-lg object-cover"
                    />
                    <button
                      type="button"
                      className="absolute -right-2 -top-2 flex h-6 w-6 items-center justify-center rounded-full bg-navy text-xs text-white"
                      onClick={(e) => {
                        e.stopPropagation()
                        setPhotoDataUrl(null)
                        setPhotoName('')
                        if (fileRef.current) fileRef.current.value = ''
                      }}
                      aria-label="Remove photo"
                    >
                      ×
                    </button>
                    <p className="mt-2 text-sm font-semibold text-navy">{photoName || 'Photo ready'}</p>
                  </div>
                ) : (
                  <>
                    <UploadIcon />
                    <p className="mt-3 text-sm font-semibold text-navy">Drop photo here</p>
                    <p className="mt-1 text-xs text-text-muted">JPG/PNG · max 2.5MB</p>
                  </>
                )}
                <input
                  ref={fileRef}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={(e) => handlePhotoFile(e.target.files?.[0])}
                />
              </div>
            </div>

            {error && (
              <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
                {error}
              </p>
            )}

            <button type="submit" className="btn-primary h-14 w-full text-base">
              Search for this person
            </button>
          </form>
        )}

        {/* STEP 2 */}
        {step === 2 && (
          <div className="mx-auto flex max-w-lg flex-col items-center px-4 py-20 text-center">
            <Spinner />
            <p className="mt-6 font-display text-2xl text-navy">Searching public sources</p>
            <p className="mt-2 text-sm text-text-muted" aria-live="polite">
              {STATUS_MESSAGES[statusIdx]}
            </p>
            <div className="lookup-progress-track mt-8">
              <div
                className="h-full rounded-[3px] bg-gold transition-[width] duration-500 ease-out"
                style={{ width: `${Math.max(progress, 4)}%` }}
              />
            </div>
            <button type="button" className="btn-secondary mt-8" onClick={resetAll}>
              Cancel
            </button>
          </div>
        )}

        {/* STEP 3 */}
        {step === 3 && report && (
          <div className="space-y-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm text-text-muted">
                Report ID <span className="font-mono text-navy">{report.report_id}</span>
                {report.cached ? ' · served from 1-hour cache' : ''}
              </p>
              <button type="button" className="btn-secondary" onClick={resetAll}>
                New search
              </button>
            </div>
            <ReportCard report={report} />
          </div>
        )}
      </div>
    </div>
  )
}
