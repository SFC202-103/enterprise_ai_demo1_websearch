import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import DemoPage from '../components/DemoPage'

// Simple smoke test to ensure admin controls render and can call tracked setter
describe('DemoPage admin UI', () => {
  beforeEach(() => {
    global.fetch = jest.fn().mockImplementation((url, opts) => {
      if (url === '/api/tracked' && opts && opts.method === 'POST') {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ tracked: { match_id: 'm1', team: 'Home' } }) })
      }
      if (url === '/api/matches') {
        return Promise.resolve({ ok: true, json: () => Promise.resolve([]) })
      }
      if (url.startsWith('/api/matches/')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ title: 'A vs B' }) })
      }
      return Promise.resolve({ ok: false })
    })
  })

  it('renders admin inputs and Set Tracked button', async () => {
    render(<DemoPage />)
    expect(await screen.findByPlaceholderText('X-Admin-Token')).toBeInTheDocument()
    const setBtn = screen.getByText('Set Tracked')
    expect(setBtn).toBeInTheDocument()
    fireEvent.click(setBtn)
    // assert fetch was called
    expect(global.fetch).toHaveBeenCalled()
  })
})
