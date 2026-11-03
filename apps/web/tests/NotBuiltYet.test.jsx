import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import NotBuiltYet from '@/pages/NotBuiltYet'

describe('NotBuiltYet', () => {
  it('renders placeholder with a title, says designed but not built yet, and does not mention Nov or prototype (A)', () => {
    render(
      <MemoryRouter>
        <NotBuiltYet title="Oil spills" />
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: 'Oil spills' })).toBeTruthy()
    expect(screen.getByText('This screen is designed but not built yet.')).toBeTruthy()
    expect(document.body.textContent).not.toContain('Nov')
    expect(document.body.textContent).not.toContain('prototype')
  })
})
