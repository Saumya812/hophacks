/**
 * Natural-language + zip alert signup panel for the homepage.
 */
import { useState } from 'react'
import { createNLAlert, createZipAlert, forgetSearch, recallSearch, rememberSearch } from '../advancedApi.js'

const PARTICIPANT_KEY = 'fmp-demo-participant'

export default function AlertsAndMemoryPanel() {
  const [nlEmail, setNlEmail] = useState('')
  const [nlQuery, setNlQuery] = useState('')
  const [zipEmail, setZipEmail] = useState('')
  const [zip, setZip] = useState('')
  const [city, setCity] = useState('')
  const [msg, setMsg] = useState('')
  const [memory, setMemory] = useState(null)

  return (
    <section className="grid gap-4 lg:grid-cols-2">
      <div className="surface-card space-y-3 p-5">
        <h2 className="font-display text-2xl text-navy">Natural-language alerts</h2>
        <p className="text-sm text-text-muted">
          Example: “Alert me if anyone reports seeing a young woman with red hair near Johns Hopkins campus”
        </p>
        <input
          className="input-field"
          placeholder="Your email"
          value={nlEmail}
          onChange={(e) => setNlEmail(e.target.value)}
        />
        <textarea
          className="input-field min-h-[90px]"
          placeholder="Alert in plain English…"
          value={nlQuery}
          onChange={(e) => setNlQuery(e.target.value)}
        />
        <button
          type="button"
          className="btn-primary"
          onClick={async () => {
            try {
              await createNLAlert({ email: nlEmail, query_text: nlQuery })
              setMsg('NL alert saved — matching tips will log an email digest.')
            } catch (err) {
              setMsg(err.message)
            }
          }}
        >
          Save alert
        </button>
      </div>

      <div className="surface-card space-y-3 p-5">
        <h2 className="font-display text-2xl text-navy">Zip code alerts</h2>
        <p className="text-sm text-text-muted">Get notified when new cases appear near your zip.</p>
        <input
          className="input-field"
          placeholder="Email"
          value={zipEmail}
          onChange={(e) => setZipEmail(e.target.value)}
        />
        <input
          className="input-field"
          placeholder="Zip e.g. 21201"
          value={zip}
          onChange={(e) => setZip(e.target.value)}
        />
        <button
          type="button"
          className="btn-primary"
          onClick={async () => {
            try {
              await createZipAlert({ email: zipEmail, zip_code: zip })
              setMsg('Zip alert saved.')
            } catch (err) {
              setMsg(err.message)
            }
          }}
        >
          Subscribe
        </button>

        <div className="border-t border-navy/10 pt-3">
          <p className="text-sm font-semibold text-navy">Search memory (Backboard stand-in)</p>
          <input
            className="input-field mt-2"
            placeholder="City to remember"
            value={city}
            onChange={(e) => setCity(e.target.value)}
          />
          <div className="mt-2 flex flex-wrap gap-2">
            <button
              type="button"
              className="btn-secondary"
              onClick={async () => {
                const r = await rememberSearch({
                  participant_key: PARTICIPANT_KEY,
                  city,
                  filters: { city },
                })
                setMsg(r.note || 'Saved')
              }}
            >
              Remember city
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={async () => {
                const r = await recallSearch(PARTICIPANT_KEY)
                setMemory(r)
                setMsg(r.found ? `Recalled city: ${r.memory?.city}` : 'No memory')
              }}
            >
              Recall
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={async () => {
                await forgetSearch(PARTICIPANT_KEY)
                setMemory(null)
                setMsg('Forgot search context')
              }}
            >
              Forget my search context
            </button>
          </div>
          {memory?.found && (
            <p className="mt-2 text-xs text-navy/55">
              Provider: {memory.provider} · backboard_live={String(memory.backboard_live)}
            </p>
          )}
        </div>
      </div>

      {msg && <p className="text-sm text-navy/70 lg:col-span-2">{msg}</p>}
    </section>
  )
}
