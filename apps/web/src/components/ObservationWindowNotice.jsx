import { windowRangeIST } from '../lib/format'

/**
 * The selected historical dates are separate from stored source/source_mode labels.
 * Observation times on the page remain the stored values; this notice only names the selection.
 */
export default function ObservationWindowNotice({ window, assessmentWindow, windowMatch, className = '' }) {
  if (window?.mode !== 'historical') return null

  const missing = !window.start || !window.end
  const assessmentMissing = assessmentWindow && (!assessmentWindow.start || !assessmentWindow.end)

  return (
    <div
      role="note"
      aria-label="Historical observation window"
      className={`rounded-md border border-line bg-canvas px-3 py-2 text-[13px] text-muted ${className}`}
    >
      <p>
        <b className="text-ink">Historical observation window</b>
        {missing ? ' · anchors not reported' : ` · ${windowRangeIST(window)}`}
      </p>
      {!missing && (
        <p className="mt-1">
          UTC {window.start} to {window.end}. Observation times below are stored values, not live data.
        </p>
      )}
      {assessmentWindow !== undefined && (
        <p className="mt-1">
          {assessmentWindow && !assessmentMissing
            ? `Assessment window ${assessmentWindow.start} to ${assessmentWindow.end}${
                windowMatch === true ? ' · matches the report window' : windowMatch === false ? ' · does not match the report window' : ''
              }.`
            : 'Assessment window anchors were not reported.'}
        </p>
      )}
    </div>
  )
}
