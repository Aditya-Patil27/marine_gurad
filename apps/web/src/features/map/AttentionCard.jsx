import { Link } from 'react-router-dom'
import StateGlyph from '../../components/StateGlyph'
import { LEVEL, score, withDisplayNames } from '../../lib/format'

export default function AttentionCard({ vessels, allVessels, selectedMmsi, onSelect, loading }) {
  return (
    <section className="card absolute left-5 top-[76px] z-10 flex max-h-[calc(100%-200px)] w-[340px] flex-col overflow-hidden" aria-labelledby="attention-title">
      <div className="flex items-baseline gap-2 px-[18px] pb-2.5 pt-4">
        <h2 id="attention-title" className="text-[19px]">Needs attention</h2>
        <span className="num text-faint">{vessels.length}</span>
        <Link to="/alerts" className="ml-auto text-[13px] text-navy-2 hover:underline">
          All alerts
        </Link>
      </div>

      <ul className="overflow-y-auto">
        {loading && !vessels.length && <li className="border-t border-line px-[18px] py-4 text-muted">Loading vessels…</li>}
        {!loading && !vessels.length && (
          <li className="border-t border-line px-[18px] py-4 text-muted">Nothing needs attention in the last 24 h.</li>
        )}
        {vessels.map((v) => {
          const selected = v.mmsi === selectedMmsi
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
                    {withDisplayNames(v.reasons.slice(1).join(' · '), allVessels) || LEVEL[v.level].label}
                  </span>
                </span>
                <span className={`num pt-px text-[13px] font-medium ${LEVEL[v.level].color}`}>{score(v.score)}</span>
              </button>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
