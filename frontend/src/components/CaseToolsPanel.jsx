/**
 * Family / community tools on the profile page.
 * Keeps the high-value actions (share kit + resolve/verify).
 * Activity / watchers / coordinators stay hidden until they have real data.
 */
import { useEffect, useState } from 'react'
import { API_BASE } from '../api.js'
import {
  flagCase,
  getEngagement,
  getSocialKit,
  listClusters,
  markFound,
  recordShare,
  renewCase,
  requestCaseAudio,
  verifyPolice,
} from '../advancedApi.js'

function copyText(text) {
  return navigator.clipboard.writeText(text)
}

export default function CaseToolsPanel({ person, onPersonChange }) {
  const [engagement, setEngagement] = useState(null)
  const [social, setSocial] = useState(null)
  const [clusters, setClusters] = useState([])
  const [msg, setMsg] = useState('')
  const [policeNo, setPoliceNo] = useState(person.police_report_number || '')
  const [audio, setAudio] = useState(null)

  async function reload() {
    const [e, cl] = await Promise.all([getEngagement(person.id), listClusters(person.id)])
    setEngagement(e)
    setClusters(cl.clusters || [])
  }

  useEffect(() => {
    reload().catch(() => {})
  }, [person.id])

  async function run(fn, okMsg) {
    setMsg('')
    try {
      const r = await fn()
      if (r && r.skipped) return r
      setMsg(okMsg || 'Done')
      await reload()
      return r
    } catch (err) {
      setMsg(err.message)
      return null
    }
  }

  const staleDays = (() => {
    const raw = person.last_verified_at || person.created_at
    if (!raw) return null
    const days = (Date.now() - new Date(raw).getTime()) / 86400000
    return Math.floor(days)
  })()

  const engagementWorthShowing = (() => {
    if (!engagement) return false
    const watchers = Number(engagement.watchers ?? 0)
    const tips = Number(engagement.tips_submitted ?? engagement.tips ?? 0)
    const shares = Number(engagement.shares ?? 0)
    return watchers > 0 || tips > 0 || shares > 0
  })()

  return (
    <div className="space-y-6">
      {person.status === 'found' && (
        <div className="border border-emerald-700/30 bg-emerald-50 px-4 py-3 text-emerald-950">
          <p className="font-display text-2xl">Found Safe</p>
          <p className="text-sm">{person.found_message || 'This case was marked resolved.'}</p>
        </div>
      )}

      {person.verified_police_report && (
        <p className="inline-block border border-navy/20 bg-navy px-3 py-1 text-xs font-bold uppercase tracking-wide text-white">
          Verified Case
        </p>
      )}
      {person.under_review && (
        <p className="inline-block border border-amber-400 bg-amber-50 px-3 py-1 text-xs font-bold uppercase text-amber-950">
          Under review
        </p>
      )}
      {staleDays != null && staleDays > 0 && (
        <p className="text-sm text-navy/60">
          Last verified by family:{' '}
          {staleDays === 1 ? '1 day ago' : `${staleDays} days ago`}
          {staleDays > 90 ? ' — renewal recommended (90-day policy)' : ''}
        </p>
      )}

      {engagementWorthShowing && (
        <p className="font-display text-lg text-navy">{engagement.label}</p>
      )}

      {msg && <p className="text-sm text-navy/70">{msg}</p>}

      {/* Social kit */}
      <section className="surface-panel p-4">
        <h3 className="font-display text-xl text-navy">Social media post kit</h3>
        <p className="mt-1 text-sm text-navy/55">
          Copy-ready posts so family can share this case on social platforms.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            className="btn-secondary"
            onClick={async () => {
              const kit = social || (await getSocialKit(person.id))
              setSocial(kit)
            }}
          >
            Load posts
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => run(() => recordShare(person.id), 'Share counted')}
          >
            Count a share
          </button>
        </div>
        {social && (
          <div className="mt-3 space-y-2">
            {Object.entries(social.posts || {}).map(([platform, text]) => (
              <div key={platform} className="border border-navy/10 bg-cream p-3">
                <div className="mb-1 flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wide text-navy/50">
                    {platform}
                  </span>
                  <button
                    type="button"
                    className="text-xs font-semibold text-navy underline"
                    onClick={() => copyText(text).then(() => setMsg(`Copied ${platform} post`))}
                  >
                    Copy
                  </button>
                </div>
                <p className="whitespace-pre-wrap text-sm text-navy/80">{text}</p>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Clusters — only when tip clusters exist */}
      {clusters.length > 0 && (
        <section className="border border-amber-300 bg-amber-50 p-4 text-amber-950">
          <h3 className="font-display text-xl">Tip cluster alerts</h3>
          <ul className="mt-2 space-y-2 text-sm">
            {clusters.map((c) => (
              <li key={c.id || `${c.center_lat}-${c.created_at}`}>
                {c.label || `${c.tip_count} tips clustered`} ({c.center_lat?.toFixed?.(3)},{' '}
                {c.center_lng?.toFixed?.(3)})
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Safety / found / verify / audio */}
      <section className="surface-panel space-y-3 p-4">
        <h3 className="font-display text-xl text-navy">Safety & resolution</h3>
        <p className="text-sm text-navy/55">
          Verify with a police report #, renew a stale case, or mark the person found safe.
        </p>
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            className="input-field"
            placeholder="Police report #"
            value={policeNo}
            onChange={(e) => setPoliceNo(e.target.value)}
          />
          <button
            type="button"
            className="btn-secondary"
            onClick={() =>
              run(async () => {
                const r = await verifyPolice(person.id, { police_report_number: policeNo })
                onPersonChange?.(r.person)
              }, 'Verified badge applied')
            }
          >
            Verify case
          </button>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="btn-secondary"
            onClick={() =>
              run(async () => {
                const r = await renewCase(person.id)
                onPersonChange?.({ ...person, last_verified_at: r.last_verified_at })
              }, 'Case renewed')
            }
          >
            Renew (90-day)
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => run(() => flagCase(person.id, { reason: 'suspicious' }), 'Flag recorded')}
          >
            Flag suspicious
          </button>
          {person.status !== 'found' && (
            <button
              type="button"
              className="btn-primary"
              onClick={() =>
                run(async () => {
                  if (
                    !window.confirm(
                      'Mark this case as found safe? This updates the public profile.',
                    )
                  ) {
                    return { skipped: true }
                  }
                  const r = await markFound(person.id, { message: 'Found safe' })
                  onPersonChange?.(r.person)
                }, 'Marked found — thank-you notices logged (not emailed unless SMTP is set)')
              }
            >
              Mark found safe
            </button>
          )}
        </div>

        <div className="border-t border-navy/10 pt-3">
          <p className="text-sm font-semibold text-navy">Read this profile aloud (ElevenLabs)</p>
          <button
            type="button"
            className="btn-secondary mt-2"
            onClick={() =>
              run(async () => {
                const r = await requestCaseAudio(person.id, {})
                setAudio(r)
                return r
              }, 'Audio request complete')
            }
          >
            Generate audio appeal
          </button>
          {audio && (
            <div className="mt-2 text-sm text-navy/75">
              <p className="whitespace-pre-wrap">{audio.transcript}</p>
              {audio.unavailable ? (
                <p className="mt-1 text-amber-800">{audio.message}</p>
              ) : (
                <audio className="mt-2 w-full" controls src={`${API_BASE}${audio.audio_url}`} />
              )}
            </div>
          )}
        </div>
      </section>
    </div>
  )
}
