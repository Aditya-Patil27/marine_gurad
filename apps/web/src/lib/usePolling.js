import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Calls `load` now and every `intervalMs`, keeping the last good data on screen if a refresh fails.
 * Pass `null` as load to pause (e.g. nothing selected).
 */
export default function usePolling(load, intervalMs, deps = []) {
  const [state, setState] = useState({ data: null, error: null, loading: Boolean(load), updatedAt: null })
  const loadRef = useRef(load)
  loadRef.current = load

  const refresh = useCallback(async () => {
    if (!loadRef.current) return
    try {
      const data = await loadRef.current()
      setState({ data, error: null, loading: false, updatedAt: new Date() })
    } catch (error) {
      setState((s) => ({ ...s, error, loading: false }))
    }
  }, [])

  useEffect(() => {
    if (!load) {
      setState({ data: null, error: null, loading: false, updatedAt: null })
      return undefined
    }
    setState((s) => ({ ...s, loading: true }))
    refresh()
    const id = setInterval(refresh, intervalMs)
    return () => clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return { ...state, refresh }
}
