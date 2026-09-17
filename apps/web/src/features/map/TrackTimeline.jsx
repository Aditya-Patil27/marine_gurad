import { useEffect, useRef, useState } from 'react'
import { hoursLabel, timeIST, vesselName } from '../../lib/format'

const WINDOW_H = 12
const PAD = 8

/** Last 12 hours of the selected vessel: when it was transmitting, when it went quiet, who it met. */
export default function TrackTimeline({ detail }) {
  const ref = useRef(null)
  const [width, setWidth] = useState(600)

  useEffect(() => {
    const el = ref.current
    if (!el) return undefined
    const ro = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const end = new Date(detail.generated_at).getTime()
  const start = end - WINDOW_H * 3600e3
  const x = (iso) => {
    const t = Math.min(end, Math.max(start, new Date(iso).getTime()))
    return PAD + ((t - start) / (end - start)) * (width - PAD * 2)
  }
  const visible = (a, b) => new Date(b).getTime() > start && new Date(a).getTime() < end

  const first = detail.track[0]?.t
  const gaps = detail.gaps.filter((g) => visible(g.start, g.end))
  const enc = detail.encounters.find((e) => visible(e.start, e.end))
  const longest = gaps.reduce((a, g) => (!a || g.hours > a.hours ? g : a), null)
  const ticks = Array.from({ length: 5 }, (_, i) => start + (i * WINDOW_H * 3600e3) / 4)

  return (
    <div
      ref={ref}
      className="card absolute bottom-5 left-[380px] right-[440px] z-10 h-[78px] px-[18px] py-2.5"
      role="img"
      aria-label={`Last ${WINDOW_H} hours of AIS for ${vesselName(detail)}`}
    >
      <svg width="100%" height="58" className="overflow-visible">
        {/* Everything we have positions for, then gaps drawn on top */}
        {first && <rect x={x(first)} y={20} width={Math.max(0, x(detail.last_seen) - x(first))} height={8} rx={4} fill="#C1CBFF" />}
        {gaps.map((g) => (
          <rect key={g.start} x={x(g.start)} y={20} width={Math.max(2, x(g.end) - x(g.start))} height={8} rx={4} fill="#FCEBEB" stroke="#D64545" strokeDasharray="3 3" />
        ))}
        {longest && longest.hours >= 1 && (
          <text x={x(longest.start) + 2} y={13} fill="#A82E2E" fontSize="12" fontFamily="Jost">
            AIS silent {hoursLabel(longest.hours)}
          </text>
        )}
        {enc && (
          <>
            <rect x={x(enc.start)} y={31} width={Math.max(2, x(enc.end) - x(enc.start))} height={3} rx={1.5} fill="#D64545" />
            <text
              x={x(enc.start)}
              y={13}
              fill="#56607A"
              fontSize="12"
              fontFamily="Jost"
              textAnchor={longest && Math.abs(x(longest.start) - x(enc.start)) < 160 ? 'end' : 'start'}
            >
              Met {vesselName(enc)}
            </text>
          </>
        )}
        {ticks.map((t, i) => (
          <text
            key={t}
            x={PAD + (i / 4) * (width - PAD * 2)}
            y={52}
            fill="#8A93A8"
            fontSize="11.5"
            fontFamily="IBM Plex Mono"
            textAnchor={i === 0 ? 'start' : i === 4 ? 'end' : 'middle'}
          >
            {i === 4 ? 'Now' : timeIST(new Date(t).toISOString())}
          </text>
        ))}
      </svg>
    </div>
  )
}
