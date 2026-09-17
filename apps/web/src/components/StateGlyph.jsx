/**
 * Vessel state is never colour alone: flagged is a solid ring, watch a dashed ring, tracked an arrow.
 * Keep in sync with the map symbols in OceanMap.
 */
export const STATE_STYLE = {
  flagged: { color: '#D64545', label: 'Flagged' },
  watch: { color: '#D98A0B', label: 'Watch' },
  tracked: { color: '#56607A', label: 'Tracked' },
}

export default function StateGlyph({ state, size = 12 }) {
  const { color } = STATE_STYLE[state] ?? STATE_STYLE.tracked
  return (
    <svg width={size} height={size} viewBox="0 0 12 12" aria-hidden="true" className="flex-none">
      {state === 'tracked' ? (
        <path d="M6 1 10 11 6 8.5 2 11Z" fill={color} />
      ) : (
        <circle cx="6" cy="6" r="4.5" fill="none" stroke={color} strokeWidth="2" strokeDasharray={state === 'watch' ? '2.5 2' : undefined} />
      )}
    </svg>
  )
}
