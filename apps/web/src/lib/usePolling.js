import { useCallback, useEffect, useRef, useState } from 'react'

const IDLE = { data: null, error: null, loading: false, updatedAt: null }
const sameDeps = (a, b) => a.length === b.length && a.every((v, i) => Object.is(v, b[i]))

/**
 * Calls `load` now and every `intervalMs`, keeping the last good data on screen if a refresh fails.
 * Pass `null` as load to pause (e.g. nothing selected). A tab in the background pauses by itself.
 * `deps` name what is being loaded: when they change, the old data and error are dropped at once.
 */
export default function usePolling(load, intervalMs, deps = []) {
  const [state, setState] = useState({ ...IDLE, loading: Boolean(load) })
  const loadRef = useRef(load)
  loadRef.current = load

  // Reset while rendering, not in the effect, so the old vessel's error is never painted for the new one
  const [seen, setSeen] = useState(deps)
  if (!sameDeps(seen, deps)) {
    setSeen(deps)
    setState({ ...IDLE, loading: Boolean(load) })
  }

  // Goes up when deps change or the component unmounts; an answer to an earlier run is dropped
  const run = useRef(0)
  const lastStart = useRef(0)

  const poll = useCallback(async () => {
    if (!loadRef.current) return
    const mine = run.current
    lastStart.current = Date.now()
    try {
      const data = await loadRef.current()
      if (mine === run.current) setState({ data, error: null, loading: false, updatedAt: new Date() })
    } catch (error) {
      if (mine === run.current) setState((s) => ({ ...s, error, loading: false }))
    }
  }, [])

  /** Load again now and say so, for a "Try again" button. Scheduled polls stay silent. */
  const refresh = useCallback(() => {
    if (loadRef.current) setState((s) => ({ ...s, loading: true }))
    return poll()
  }, [poll])

  useEffect(() => {
    if (!load) return undefined
    poll()
    // Nobody is looking at a background tab: its polls are skipped, and one that came due runs when it is shown again
    const id = setInterval(() => document.hidden || poll(), intervalMs)
    const onShow = () => !document.hidden && Date.now() - lastStart.current >= intervalMs && poll()
    document.addEventListener('visibilitychange', onShow)
    return () => {
      clearInterval(id)
      document.removeEventListener('visibilitychange', onShow)
      run.current += 1
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return { ...state, refresh }
}
