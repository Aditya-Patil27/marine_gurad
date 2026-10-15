import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import usePolling from '@/lib/usePolling'

/** A promise the test settles by hand, to control the order responses arrive in. */
function deferred() {
  let resolve
  let reject
  const promise = new Promise((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

const down = () => Promise.reject(new Error('down'))

/** Polls `loads[id]`, the way the map page polls the selected vessel. */
const pollById = (loads, id) =>
  renderHook(({ id }) => usePolling(loads[id] ?? null, 30000, [id]), { initialProps: { id } })

/** Puts the page in a background tab, or brings it back to the front. */
function setHidden(hidden) {
  Object.defineProperty(document, 'hidden', { configurable: true, get: () => hidden })
  document.dispatchEvent(new Event('visibilitychange'))
}

afterEach(() => {
  vi.useRealTimers()
  delete document.hidden
})

describe('usePolling', () => {
  it('keeps the last good data when a later poll fails', async () => {
    vi.useFakeTimers()
    let calls = 0
    const load = () => (calls++ === 0 ? Promise.resolve('first') : down())
    const { result } = renderHook(() => usePolling(load, 1000))

    await act(() => vi.advanceTimersByTimeAsync(0))
    expect(result.current).toMatchObject({ data: 'first', error: null, loading: false })

    await act(() => vi.advanceTimersByTimeAsync(1000))
    expect(result.current.data).toBe('first')
    expect(result.current.error).toBeInstanceOf(Error)
  })

  it('forgets the previous error as soon as the deps change', async () => {
    const { result, rerender } = pollById({ a: down, b: () => deferred().promise }, 'a')
    await waitFor(() => expect(result.current.error).toBeInstanceOf(Error))

    rerender({ id: 'b' })

    expect(result.current).toMatchObject({ error: null, loading: true })
  })

  it('forgets the previous data as soon as the deps change', async () => {
    const { result, rerender } = pollById({ a: () => Promise.resolve('A'), b: () => deferred().promise }, 'a')
    await waitFor(() => expect(result.current.data).toBe('A'))

    rerender({ id: 'b' })

    expect(result.current).toMatchObject({ data: null, loading: true })
  })

  it('ignores a response that lands after the deps moved on', async () => {
    const slow = deferred()
    const { result, rerender } = pollById({ a: () => slow.promise, b: () => Promise.resolve('B') }, 'a')

    rerender({ id: 'b' })
    await waitFor(() => expect(result.current.data).toBe('B'))
    await act(async () => slow.resolve('A'))

    expect(result.current).toMatchObject({ data: 'B', loading: false })
  })

  it('ignores a failure that lands after the deps moved on', async () => {
    const slow = deferred()
    const { result, rerender } = pollById({ a: () => slow.promise, b: () => Promise.resolve('B') }, 'a')

    rerender({ id: 'b' })
    await waitFor(() => expect(result.current.data).toBe('B'))
    await act(async () => slow.reject(new Error('late')))

    expect(result.current).toMatchObject({ data: 'B', error: null })
  })

  it('ignores a response that lands after polling was paused', async () => {
    const slow = deferred()
    const { result, rerender } = pollById({ a: () => slow.promise }, 'a')

    rerender({ id: null })
    await act(async () => slow.resolve('A'))

    expect(result.current).toMatchObject({ data: null, loading: false })
  })

  it('reports loading while a manual refresh is in flight, then clears the error', async () => {
    const retry = deferred()
    let calls = 0
    const load = () => (calls++ === 0 ? down() : retry.promise)
    const { result } = renderHook(() => usePolling(load, 30000))
    await waitFor(() => expect(result.current).toMatchObject({ loading: false, error: expect.any(Error) }))

    act(() => {
      result.current.refresh()
    })
    expect(result.current.loading).toBe(true)

    await act(async () => retry.resolve('ok'))
    expect(result.current).toMatchObject({ data: 'ok', error: null, loading: false })
  })

  it('skips polls while the page is in a background tab', async () => {
    vi.useFakeTimers()
    const load = vi.fn().mockResolvedValue('x')
    renderHook(() => usePolling(load, 1000))
    await act(() => vi.advanceTimersByTimeAsync(0))

    act(() => setHidden(true))
    await act(() => vi.advanceTimersByTimeAsync(5000))

    expect(load).toHaveBeenCalledTimes(1)
  })

  it('catches up as soon as the page is shown again', async () => {
    vi.useFakeTimers()
    const load = vi.fn().mockResolvedValue('x')
    renderHook(() => usePolling(load, 1000))
    await act(() => vi.advanceTimersByTimeAsync(0))
    act(() => setHidden(true))
    await act(() => vi.advanceTimersByTimeAsync(5000))

    await act(async () => setHidden(false))

    expect(load).toHaveBeenCalledTimes(2)
  })

  it('does not load again on coming back while the last answer is still fresh', async () => {
    vi.useFakeTimers()
    const load = vi.fn().mockResolvedValue('x')
    renderHook(() => usePolling(load, 10000))
    await act(() => vi.advanceTimersByTimeAsync(0))
    act(() => setHidden(true))
    await act(() => vi.advanceTimersByTimeAsync(2000))

    await act(async () => setHidden(false))

    expect(load).toHaveBeenCalledTimes(1)
  })
})
