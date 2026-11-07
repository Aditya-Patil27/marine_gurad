import { createContext, useCallback, useContext, useMemo, useState } from 'react'

export const ROLLING_HOURS = 168

/** The one prepared replay the UI offers. Bounds are UTC and inclusive at the end. */
export const REPLAY_PRESET = Object.freeze({
  mode: 'historical',
  start: '2026-10-30T00:00:00Z',
  end: '2026-11-02T00:00:00Z',
  hours: 72,
})

export const ROLLING_WINDOW = Object.freeze({
  mode: 'rolling',
  start: null,
  end: null,
  hours: ROLLING_HOURS,
})

const STORAGE_KEY = 'samudrasense.observation-window'

/** A stable key for polling dependencies, so an old selection's answer is dropped. */
export const windowKey = (window) =>
  window?.mode === 'historical' && window.start && window.end ? `${window.start}/${window.end}` : 'rolling'

/** The two request values, or null for rolling. Rolling callers must omit both fields. */
export const windowBounds = (window) =>
  window?.mode === 'historical' && window.start && window.end ? window : null

/** Exact equality over the persisted anchors, not just the duration. */
export const sameWindow = (a, b) =>
  Boolean(a && b) && a.mode === b.mode && a.start === b.start && a.end === b.end

function storedWindow() {
  try {
    return globalThis.sessionStorage?.getItem(STORAGE_KEY) === 'historical' ? REPLAY_PRESET : ROLLING_WINDOW
  } catch {
    return ROLLING_WINDOW
  }
}

function remember(window) {
  try {
    globalThis.sessionStorage?.setItem(STORAGE_KEY, window.mode === 'historical' ? 'historical' : 'rolling')
  } catch {
    // A browser with storage disabled still keeps the in-memory selection for this visit.
  }
}

// Pages can be rendered alone in tests and previews; they then behave as the ordinary rolling view.
const DEFAULT = {
  window: ROLLING_WINDOW,
  setWindow: () => {},
  selectRolling: () => {},
  selectReplay: () => {},
  isHistorical: false,
  bounds: null,
  key: 'rolling',
}

const ReplayWindowContext = createContext(DEFAULT)

export function ReplayWindowProvider({ children }) {
  const [window, setWindowState] = useState(storedWindow)

  const setWindow = useCallback((next) => {
    const normalized = next === 'historical' || next === REPLAY_PRESET ? REPLAY_PRESET : ROLLING_WINDOW
    setWindowState(normalized)
    remember(normalized)
  }, [])

  const selectRolling = useCallback(() => setWindow(ROLLING_WINDOW), [setWindow])
  const selectReplay = useCallback(() => setWindow(REPLAY_PRESET), [setWindow])

  const value = useMemo(
    () => ({
      window,
      setWindow,
      selectRolling,
      selectReplay,
      isHistorical: window.mode === 'historical',
      bounds: windowBounds(window),
      key: windowKey(window),
    }),
    [window, setWindow, selectRolling, selectReplay],
  )

  return <ReplayWindowContext.Provider value={value}>{children}</ReplayWindowContext.Provider>
}

export function useReplayWindow() {
  return useContext(ReplayWindowContext)
}
