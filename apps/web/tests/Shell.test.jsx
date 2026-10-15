import { act, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Shell from '@/components/Shell'
import { vesselsApi } from '@/lib/api'
import { fleet } from './fixtures'

vi.mock('@/lib/api', async (original) => ({
  ...(await original()),
  vesselsApi: { list: vi.fn(), get: vi.fn() },
}))

let healthy = false
function Flaky() {
  if (!healthy) throw new Error('This page cannot draw')
  return <p>Page drawn</p>
}

async function open(url) {
  render(
    <MemoryRouter initialEntries={[url]}>
      <Routes>
        <Route element={<Shell />}>
          <Route path="map" element={<Flaky />} />
          <Route path="alerts" element={<p>Alerts page</p>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
  await act(async () => {})
}

// React and jsdom both report an error a boundary catches; here it is thrown on purpose
const expected = (event) => event.preventDefault()

beforeEach(() => {
  healthy = false
  vesselsApi.list.mockReset().mockResolvedValue(fleet)
  vi.spyOn(console, 'error').mockImplementation(() => {})
  window.addEventListener('error', expected)
})

afterEach(() => {
  window.removeEventListener('error', expected)
  vi.restoreAllMocks()
})

describe('shell', () => {
  it('says how many vessels are high risk on the Alerts link', async () => {
    await open('/alerts')

    expect(screen.getByRole('link', { name: 'Alerts, 1 high risk' })).toBeTruthy()
  })

  it('keeps the rail when a page fails to draw', async () => {
    await open('/map')

    expect(screen.getByRole('navigation', { name: 'Main' })).toBeTruthy()
    expect(screen.getByRole('alert').textContent).toContain('This screen stopped working')
  })

  it('draws the page again when asked', async () => {
    await open('/map')
    healthy = true

    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))

    expect(screen.getByText('Page drawn')).toBeTruthy()
  })

  it('leaves the failure behind when another page is opened', async () => {
    await open('/map')

    fireEvent.click(screen.getByRole('link', { name: /Alerts/ }))

    expect(screen.getByText('Alerts page')).toBeTruthy()
  })
})
