import { Link } from 'react-router-dom'
import { CircleAlert } from 'lucide-react'
import StateGlyph from '../../components/StateGlyph'
import { levelStyle, score, timeIST, withDisplayNames } from '../../lib/format'

export default function AttentionCard({ vessels, allVessels, selectedMmsi, onSelect, loading, error, updatedAt, onRetry }) {
  // Until the first answer there is no list to count; after it, a failed refresh makes the list old, not empty
  const loaded = Boolean(updatedAt)
  const failed = !loaded && error && !loading
  const staleSince = loaded && error ? timeIST(updatedAt) : null

  let empty = allVessels.length ? 'Nothing needs attention in the last 24 h.' : 'No vessel has reported in the last 24 h.'
  if (staleSince) empty = allVessels.length ? `Nothing needed attention at ${staleSince}.` : `No vessel had reported at ${staleSince}.`

  return (
    <section className="card absolute left-5 top-[76px] z-10 flex max-h-[calc(100%-200px)] w-[340px] flex-col overflow-hidden" aria-labelledby="attention-title">
      <div className="flex items-baseline gap-2 px-[18px] pb-2.5 pt-4">
        <h2 id="attention-title" className="text-[19px]">Needs attention</h2>
        {loaded && <span className="num text-faint">{vessels.length}</span>}
        <Link to="/alerts" className="ml-auto text-[13px] text-navy-2 hover:underline">
          All alerts
        </Link>
      </div>

      {staleSince && (
        <p role="alert" className="flex gap-2 border-t border-line bg-canvas px-[18px] py-2.5 text-[13px] text-muted">
          <CircleAlert size={15} className="mt-0.5 flex-none text-risk-amber" aria-hidden="true" />
          Not updating. This list is from {staleSince}.
        </p>
      )}

      <ul className="overflow-y-auto">
        {!loaded && !failed && <li className="border-t border-line px-[18px] py-4 text-muted">Loading vessels…</li>}
        {failed && (
          <li role="alert" className="border-t border-line px-[18px] py-4 text-muted">
            Can't load vessels. The API isn't answering.
            <button type="button" className="btn mt-3 flex" onClick={onRetry}>
              Try again
            </button>
          </li>
        )}
        {loaded && !vessels.length && <li className="border-t border-line px-[18px] py-4 text-muted">{empty}</li>}
        {vessels.map((v) => {
          const selected = v.mmsi === selectedMmsi
          const level = levelStyle(v.level)
          return (
            <li key={v.mmsi}>
              <button
                type="button"
                onClick={() => onSelect(v.mmsi)}
                aria-pressed={selected}
                className={`grid w-full grid-cols-[14px_1fr_auto] gap-3 border-t border-line px-[18px] py-3 text-left transition-colors ${
                  selected ? 'bg-peri-soft shadow-[inset_3px_0_0_#08337F]' : 'hover:bg-canvas'
                }`}
              >
                <span className="mt-[5px]">
                  <StateGlyph state={v.state} />
                </span>
                <span className="min-w-0">
                  <b className="block font-medium">{withDisplayNames(v.headline, allVessels)}</b>
                  <span className="block text-[13px] text-muted">
                    {withDisplayNames(v.reasons.slice(1).join(' · '), allVessels) || level.label}
                  </span>
                </span>
                <span className={`num pt-px text-[13px] font-medium ${level.color}`}>{score(v.score)}</span>
              </button>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
