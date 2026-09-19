/**
 * /lookup — Smart Person Search (3-step flow on one page).
 * Step 1: name + photo input
 * Step 2: animated progress while backend scrapes
 * Step 3: intelligence report via ReportCard
 */
import { useEffect, useRef, useState } from 'react'
import { lookupSearch } from '../api.js'
import ReportCard from '../components/ReportCard.jsx'

const STATUS_MESSAGES = [
  'Searching Instagram...',
  'Scanning Facebook...',
  'Checking TikTok...',
  'Scanning X (Twitter)...',
  'Searching news comments...',
  'Reading Reddit threads...',
  'Compiling report...',
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
    }, 1800)
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
    if (!photoDataUrl) {
      setError('Upload a clear, front-facing photo to continue.')
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
        photo: photoDataUrl,
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
    <div className="space-y-8">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-navy/45">
          Smart Person Search
        </p>
        <h1 className="font-display text-3xl text-navy sm:text-4xl">Person Lookup</h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-navy/65 sm:text-base">
          Upload a photo and name. FindMyPal searches publicly indexed web and social sources,
          then compiles a structured sighting brief. Photos are kept only for this session.
        </p>
      </div>

      {/* Step indicator */}
      <ol className="grid grid-cols-3 gap-2 border border-navy/10 bg-white/80 p-2 sm:gap-3 sm:p-3">
        {STEPS.map((s) => {
          const active = step === s.id
          const done = step > s.id
          return (
            <li
              key={s.id}
              className={`px-2 py-3 text-center sm:px-3 ${
                active
                  ? 'bg-navy text-white'
                  : done
                    ? 'bg-navy-50 text-navy'
                    : 'text-navy/40'
              }`}
            >
              <p className="text-[10px] font-bold uppercase tracking-[0.16em]">Step {s.id}</p>
              <p className="mt-1 text-sm font-semibold">{s.label}</p>
            </li>
          )
        })}
      </ol>

      {/* STEP 1 */}
      {step === 1 && (
        <form onSubmit={handleSearch} className="surface-panel space-y-5 p-5 sm:p-6">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="label-field" htmlFor="firstName">
                First name
              </label>
              <input
                id="firstName"
                className="input-field"
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
                className="input-field"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                required
                autoComplete="family-name"
              />
            </div>
          </div>

          <div>
            <p className="label-field">Photo</p>
            <p className="mb-2 text-sm text-navy/60">
              Upload a clear, front-facing photo for best results
            </p>
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
                const file = e.dataTransfer.files?.[0]
                handlePhotoFile(file)
              }}
              className={`flex cursor-pointer flex-col items-center justify-center border border-dashed px-4 py-10 text-center transition-colors ${
                dragOver
                  ? 'border-navy bg-navy-50'
                  : 'border-navy/25 bg-white hover:border-navy/50'
              }`}
            >
              {photoDataUrl ? (
                <>
                  <img
                    src={photoDataUrl}
                    alt="Upload preview"
                    className="mb-3 h-28 w-24 object-cover ring-1 ring-navy/15"
                  />
                  <p className="text-sm font-semibold text-navy">{photoName || 'Photo ready'}</p>
                  <p className="mt-1 text-xs text-navy/50">Click or drop to replace</p>
                </>
              ) : (
                <>
                  <p className="font-display text-xl text-navy/70">Drop photo here</p>
                  <p className="mt-1 text-sm text-navy/50">or click to browse · JPG/PNG · max 2.5MB</p>
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
            <p className="border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
              {error}
            </p>
          )}

          <button type="submit" className="btn-primary w-full sm:w-auto">
            Search for this person
          </button>
        </form>
      )}

      {/* STEP 2 */}
      {step === 2 && (
        <div className="surface-panel space-y-5 p-6 sm:p-8">
          <p className="font-display text-2xl text-navy">Searching public sources</p>
          <p className="text-sm text-navy/60">
            Queries run in parallel across web index, news, Reddit, X, and YouTube.
          </p>
          <div className="h-2 w-full overflow-hidden bg-navy-100">
            <div
              className="h-full bg-navy transition-[width] duration-500 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-sm font-semibold tracking-wide text-navy/80" aria-live="polite">
            {STATUS_MESSAGES[statusIdx]}
          </p>
          <button type="button" className="btn-secondary" onClick={resetAll}>
            Cancel
          </button>
        </div>
      )}

      {/* STEP 3 */}
      {step === 3 && report && (
        <div className="space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-navy/55">
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
  )
}
