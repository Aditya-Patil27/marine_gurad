import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'

// The console shows India Standard Time whatever the machine is set to; UTC here proves it
process.env.TZ = 'UTC'

// jsdom has no layout, so there is never a size to report
globalThis.ResizeObserver ??= class {
  observe() {}
  disconnect() {}
}

afterEach(cleanup)
