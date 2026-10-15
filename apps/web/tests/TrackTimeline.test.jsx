import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import TrackTimeline from '@/features/map/TrackTimeline'
import { seaPearlDetail } from './fixtures'

const spoken = () => screen.getByRole('img').getAttribute('aria-label')

describe('track timeline', () => {
  it('says in words what the picture shows', () => {
    render(<TrackTimeline detail={seaPearlDetail} />)

    expect(spoken()).toBe('Last 12 hours of AIS for Sea Pearl II. AIS silent 6 h 23 m since 12:10. Met Hai Feng 818 from 09:33 to 12:00.')
  })

  it('gives both ends of a silence that is over', () => {
    const gap = { start: '2026-10-13T03:30:00Z', end: '2026-10-13T05:30:00Z', hours: 2, open: false }
    render(<TrackTimeline detail={{ ...seaPearlDetail, gaps: [gap], encounters: [] }} />)

    expect(spoken()).toBe('Last 12 hours of AIS for Sea Pearl II. AIS silent 2 h from 09:00 to 11:00.')
  })

  it('leaves out what happened before the 12 hours shown', () => {
    const old = { start: '2026-10-12T20:00:00Z', end: '2026-10-12T23:00:00Z', hours: 3, open: false }
    render(<TrackTimeline detail={{ ...seaPearlDetail, gaps: [old], encounters: [{ ...seaPearlDetail.encounters[0], ...old }] }} />)

    expect(spoken()).toBe('Last 12 hours of AIS for Sea Pearl II.')
  })
})
