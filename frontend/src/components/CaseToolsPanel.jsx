/**
 * Family / community tools on the profile page.
 */
import { useEffect, useState } from 'react'
import { API_BASE } from '../api.js'
import {
  addCaseUpdate,
  flagCase,
  getCaseActivity,
  getEngagement,
  getPlatformMentions,
  getSocialKit,
  inviteCoordinator,
  listCaseUpdates,
  listClusters,
  listCoordinators,
  markFound,
  recordShare,
  renewCase,
  requestCaseAudio,
  verifyPolice,
  watchCase,
} from '../advancedApi.js'

function copyText(text) {
  return navigator.clipboard.writeText(text)
}

function SimpleBars({ series }) {
  const max = Math.max(1, ...series.map((s) => s.tips))
  return (
    <div className="flex h-32 items-end gap-1">
      {series.map((s) => (
        <div key={s.bucket} className="flex flex-1 flex-col items-center gap-1" title={`${s.bucket}: ${s.tips}`}>
          <div
            className="w-full bg-navy"
            style={{ height: `${(s.tips / max) * 100}%`, minHeight: s.tips ? 4 : 0 }}
          />
        </div>
      ))}
    </div>
  )
}

function Donut({ slices }) {
  const total = slices.reduce((a, s) => a + s.count, 0) || 1
  let acc = 0
  const colors = ['#1a2b4a', '#4d6786', '#9aadc4', '#c5d0de', '#e4e9ef']
  const stops = slices.map((s, i) => {
    const start = (acc / total) * 100
    acc += s.count
    const end = (acc / total) * 100
    return `${colors[i % colors.length]} ${start}% ${end}%`
  })
  return (
    <div className="flex flex-wrap items-center gap-4">
      <div
        className="h-28 w-28 rounded-full"
        style={{ background: `conic-gradient(${stops.join(',')})` }}
        aria-hidden
      />
      <ul className="text-sm text-navy/75">
        {slices.map((s, i) => (
          <li key={s.platform} className="flex items-center gap-2">
            <span className="inline-block h-2 w-2" style={{ background: colors[i % colors.length] }} />
            {s.platform}: {s.pct}%
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function CaseToolsPanel({ person, onPersonChange }) {
  const [engagement, setEngagement] = useState(null)
  const [social, setSocial] = useState(null)
  const [updates, setUpdates] = useState([])
  const [coords, setCoords] = useState([])
  const [clusters, setClusters] = useState([])
  const [activity, setActivity] = useState(null)
  const [platforms, setPlatforms] = useState(null)
  const [msg, setMsg] = useState('')
  const [updateBody, setUpdateBody] = useState('')
  const [coordEmail, setCoordEmail] = useState('')
  const [watchEmail, setWatchEmail] = useState('')
  const [policeNo, setPoliceNo] = useState(person.police_report_number || '')
  const [audio, setAudio] = useState(null)

  async function reload() {
    const [e, u, c, cl, act, plat] = await Promise.all([
      getEngagement(person.id),
      listCaseUpdates(person.id),
      listCoordinators(person.id),
      listClusters(person.id),
      getCaseActivity(person.id),
      getPlatformMentions(person.id),
    ])
    setEngagement(e)
    setUpdates(u.updates || [])
    setCoords(c.coordinators || [])
    setClusters(cl.clusters || [])
    setActivity(act)
    setPlatforms(plat)
  }

  useEffect(() => {
    reload().catch(() => {})
  }, [person.id])

  async function run(fn, okMsg) {
    setMsg('')
    try {
      const r = await fn()
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
      {staleDays != null && (
        <p className="text-sm text-navy/60">
          Last verified by family:{' '}
          {staleDays === 0 ? 'today' : `${staleDays} day${staleDays === 1 ? '' : 's'} ago`}
          {staleDays > 90 ? ' — renewal recommended (90-day policy)' : ''}
        </p>
      )}

      {engagement && (
        <p className="font-display text-lg text-navy">{engagement.label}</p>
      )}

      {msg && <p className="text-sm text-navy/70">{msg}</p>}

      {/* Social kit */}
      <section className="surface-panel p-4">
        <h3 className="font-display text-xl text-navy">Social media post kit</h3>
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
              <div key={platform} className="border border-navy/10 bg-white p-3">
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

      {/* Activity explorer (marimo-track charts via API) */}
      <section className="surface-panel p-4">
        <h3 className="font-display text-xl text-navy">Activity explorer</h3>
        <p className="text-xs text-navy/50">
          Tip volume over time (API-backed). Marimo can consume the same `/analytics/case-activity` route.
        </p>
        {activity?.series?.length ? (
          <div className="mt-3">
            <SimpleBars series={activity.series} />
            <p className="mt-2 text-xs text-navy/45">{activity.total_tips} tips total</p>
          </div>
        ) : (
          <p className="mt-2 text-sm text-navy/55">No tip activity yet.</p>
        )}
        {platforms?.slices?.length > 0 && (
          <div className="mt-4">
            <p className="mb-2 text-sm font-semibold text-navy">Platform / source breakdown</p>
            <Donut slices={platforms.slices} />
          </div>
        )}
      </section>

      {/* Clusters */}
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

      {/* Updates + watch */}
      <section className="surface-panel space-y-3 p-4">
        <h3 className="font-display text-xl text-navy">Case updates & watchers</h3>
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            className="input-field"
            placeholder="Watcher email"
            value={watchEmail}
            onChange={(e) => setWatchEmail(e.target.value)}
          />
          <button
            type="button"
            className="btn-secondary"
            onClick={() =>
              run(
                () => watchCase({ email: watchEmail, person_id: person.id }),
                'Watcher added',
              )
            }
          >
            Watch case
          </button>
        </div>
        <textarea
          className="input-field min-h-[80px]"
          placeholder="Family update to broadcast…"
          value={updateBody}
          onChange={(e) => setUpdateBody(e.target.value)}
        />
        <button
          type="button"
          className="btn-primary"
          onClick={() =>
            run(async () => {
              await addCaseUpdate(person.id, { body: updateBody })
              setUpdateBody('')
            }, 'Update posted & emails logged')
          }
        >
          Broadcast update
        </button>
        <ul className="space-y-2 text-sm">
          {updates.map((u) => (
            <li key={u.id} className="border-b border-navy/10 pb-2">
              <p className="text-xs text-navy/45">{new Date(u.created_at).toLocaleString()}</p>
              <p>{u.body}</p>
            </li>
          ))}
        </ul>
      </section>

      {/* Coordinators */}
      <section className="surface-panel space-y-3 p-4">
        <h3 className="font-display text-xl text-navy">Search coordinators</h3>
        <p className="text-xs text-navy/50">Invite up to 4 people (mock roles — not real auth).</p>
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            className="input-field"
            placeholder="coordinator@email.com"
            value={coordEmail}
            onChange={(e) => setCoordEmail(e.target.value)}
          />
          <button
            type="button"
            className="btn-secondary"
            onClick={() =>
              run(() => inviteCoordinator(person.id, { email: coordEmail }), 'Coordinator invited')
            }
          >
            Invite
          </button>
        </div>
        <ul className="text-sm text-navy/75">
          {coords.map((c) => (
            <li key={c.id}>
              {c.email} · {c.role}
            </li>
          ))}
        </ul>
      </section>

      {/* Safety / found / verify / audio */}
      <section className="surface-panel space-y-3 p-4">
        <h3 className="font-display text-xl text-navy">Safety & resolution</h3>
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
                  const r = await markFound(person.id, { message: 'Found safe' })
                  onPersonChange?.(r.person)
                }, 'Marked found — thank-you emails logged')
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
