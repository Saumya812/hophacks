/**
 * Practical volunteer actions — reuses existing share / tip / flyer / source link.
 */
import { Link } from 'react-router-dom'
import FlyerButton from './FlyerButton.jsx'
import { safeHttpUrl } from '../lib/caseHelpers.js'

export default function HowYouCanHelp({ person, onShare }) {
  const listing = safeHttpUrl(person?.source_listing_url)
  const isFound = (person?.status || '').toLowerCase() === 'found'

  return (
    <section className="surface-card p-5 sm:p-6">
      <h2 className="font-display text-xl text-navy">How you can help</h2>
      <p className="mt-1 text-sm text-text-muted">
        {isFound
          ? 'This case is resolved. You can still share the reunion story.'
          : 'Practical actions only — do not approach strangers or publish accusations.'}
      </p>
      <ul className="mt-4 space-y-3 text-sm">
        <li className="flex flex-wrap items-center gap-2">
          <button type="button" className="btn-secondary" onClick={onShare}>
            Share this case
          </button>
          <span className="text-text-muted">Pass the profile link to people who may know something.</span>
        </li>
        <li className="flex flex-wrap items-center gap-2">
          <FlyerButton person={person} />
          <span className="text-text-muted">Print or post the flyer.</span>
        </li>
        {!isFound && (
          <li className="flex flex-wrap items-center gap-2">
            <Link to={`/tip/${person.id}`} className="btn-primary">
              Submit relevant information
            </Link>
            <span className="text-text-muted">Tips are community-provided and unverified.</span>
          </li>
        )}
        {listing && (
          <li className="flex flex-wrap items-center gap-2">
            <a
              href={listing}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-secondary"
            >
              View original listing
            </a>
            <span className="text-text-muted">Opens the community-provided source link.</span>
          </li>
        )}
      </ul>
    </section>
  )
}
