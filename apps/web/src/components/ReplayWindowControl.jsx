import { useReplayWindow } from '../lib/replayWindow'
import { windowRangeIST } from '../lib/format'

/** One visible rolling/historical choice, retained for the browser session. */
export default function ReplayWindowControl() {
  const { window, isHistorical, selectRolling, selectReplay } = useReplayWindow()

  return (
    <div
      role="group"
      aria-label="Observation window"
      className="flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-line bg-white px-4 py-1.5 text-[13px]"
    >
      <span className="font-medium text-ink">Observation window</span>
      <label className="flex items-center gap-1.5">
        <input type="radio" name="observation-window" checked={!isHistorical} onChange={selectRolling} />
        Rolling 7 days
      </label>
      <label className="flex items-center gap-1.5">
        <input type="radio" name="observation-window" checked={isHistorical} onChange={selectReplay} />
        Historical replay · 30 Oct–2 Nov 2026
      </label>
      {isHistorical && (
        <span className="text-muted">
          {windowRangeIST(window)} · UTC {window.start} to {window.end}
        </span>
      )}
    </div>
  )
}
