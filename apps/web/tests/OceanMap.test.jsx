import { act, render } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import OceanMap from '@/features/map/OceanMap'
import { seaPearl, seaPearlDetail } from './fixtures'

const { FakeMap, FakeMarker, FakeLngLatBounds, getLatestMap } = vi.hoisted(() => {
  let latestMap = null

  class FakeMap {
    constructor(options = {}) {
      latestMap = this
      this.options = options
      const container = options.container || { clientWidth: 1024, clientHeight: 768 }
      if (container && typeof container === 'object') {
        if (!container.clientWidth) {
          Object.defineProperty(container, 'clientWidth', { value: 1200, configurable: true })
          Object.defineProperty(container, 'clientHeight', { value: 800, configurable: true })
        }
      }
      this.container = container

      const handlers = {}
      this.handlers = handlers
      this.on = vi.fn((type, arg2, arg3) => {
        const fn = typeof arg2 === 'function' ? arg2 : arg3
        const layers = typeof arg2 === 'function' ? undefined : arg2
        handlers[type] = handlers[type] || []
        handlers[type].push({ fn, layers })
        return this
      })

      this.fire = (type, arg1, arg2) => {
        let layer
        let eventData
        if (typeof arg1 === 'string') {
          layer = arg1
          eventData = arg2 || {}
        } else {
          eventData = arg1 || {}
          layer = eventData.layer
        }
        const list = handlers[type] || []
        for (const h of list) {
          if (!layer || !h.layers || (Array.isArray(h.layers) ? h.layers.includes(layer) : h.layers === layer)) {
            h.fn(eventData)
          }
        }
      }

      const sources = new Map()
      this.sources = sources
      this.addSource = vi.fn((id, source) => {
        if (sources.has(id)) {
          throw new Error(`There is already a source with this ID: ${id}`)
        }
        const sourceObj = {
          ...source,
          setData: vi.fn(),
        }
        sources.set(id, sourceObj)
        return sourceObj
      })
      this.getSource = vi.fn((id) => sources.get(id))

      const layers = []
      this.layers = layers
      this.addLayer = vi.fn((layer) => {
        layers.push(layer)
        return this
      })

      const canvas = { style: {} }
      this.canvas = canvas
      this.getCanvas = vi.fn(() => canvas)
      this.getContainer = vi.fn(() => container)

      this.touchZoomRotate = {
        disableRotation: vi.fn(),
      }
      this.addImage = vi.fn()
      this.setLayoutProperty = vi.fn()
      this.fitBounds = vi.fn()
      this.remove = vi.fn()
    }
  }

  class FakeMarker {
    constructor(options = {}) {
      this.options = options
    }
    setLngLat(lngLat) {
      this.lngLat = lngLat
      return this
    }
    addTo(map) {
      this.map = map
      return this
    }
    remove() {
      return this
    }
  }

  class FakeLngLatBounds {
    constructor(sw, ne) {
      this.sw = sw
      this.ne = ne
    }
    extend(coord) {
      return this
    }
  }

  return {
    FakeMap,
    FakeMarker,
    FakeLngLatBounds,
    getLatestMap: () => latestMap,
  }
})

vi.mock('maplibre-gl', () => ({
  default: {
    Map: FakeMap,
    Marker: FakeMarker,
    LngLatBounds: FakeLngLatBounds,
  },
  Map: FakeMap,
  Marker: FakeMarker,
  LngLatBounds: FakeLngLatBounds,
}))

beforeEach(() => {
  const ctxStub = {
    beginPath: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    closePath: vi.fn(),
    fill: vi.fn(),
    getImageData: vi.fn(() => ({
      data: new Uint8ClampedArray(32 * 32 * 4),
      width: 32,
      height: 32,
    })),
  }
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(ctxStub)
})

describe('OceanMap', () => {
  it('passes the vessels to the vessels source and the zones to the zones source when style is ready and tiles have not finished', async () => {
    const zones = {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          geometry: { type: 'Polygon', coordinates: [] },
          properties: { kind: 'outline', name: 'Gulf of Mannar' },
        },
      ],
    }
    render(<OceanMap vessels={[seaPearl]} zones={zones} />)
    const map = getLatestMap()

    await act(async () => {
      map.fire('style.load')
    })

    const vesselsSource = map.getSource('vessels')
    const zonesSource = map.getSource('zones')

    expect(vesselsSource).toBeDefined()
    expect(zonesSource).toBeDefined()
    expect(vesselsSource.setData).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'FeatureCollection',
        features: [
          expect.objectContaining({
            properties: expect.objectContaining({ mmsi: seaPearl.mmsi }),
          }),
        ],
      }),
    )
    expect(zonesSource.setData).toHaveBeenCalledWith(zones)
  })

  it('calls onSelect with the vessel MMSI when the officer clicks the vessel-arrow layer', async () => {
    const onSelect = vi.fn()
    render(<OceanMap vessels={[seaPearl]} onSelect={onSelect} />)
    const map = getLatestMap()

    await act(async () => {
      map.fire('style.load')
    })

    await act(async () => {
      map.fire('click', 'vessel-arrow', {
        features: [{ properties: { mmsi: seaPearl.mmsi } }],
      })
    })

    expect(onSelect).toHaveBeenCalledWith(seaPearl.mmsi)
  })

  it('passes its track to the track source and calls fitBounds once when style is ready with a selected vessel', async () => {
    render(<OceanMap vessels={[seaPearl]} detail={seaPearlDetail} />)
    const map = getLatestMap()

    await act(async () => {
      map.fire('style.load')
    })

    const trackSource = map.getSource('track')
    expect(trackSource).toBeDefined()
    const sent = trackSource.setData.mock.calls.at(-1)[0]
    expect(sent.features[0].geometry.coordinates).toEqual(seaPearlDetail.track.map((p) => [p.lon, p.lat]))
    expect(map.fitBounds).toHaveBeenCalledTimes(1)
  })

  it('does not add its sources or layers a second time when load fires after style.load', async () => {
    render(<OceanMap vessels={[seaPearl]} />)
    const map = getLatestMap()

    await act(async () => {
      map.fire('style.load')
    })

    await act(async () => {
      map.fire('load')
    })

    expect(map.getSource('vessels')).toBeDefined()
    expect(map.getSource('zones')).toBeDefined()
    expect(map.getSource('track')).toBeDefined()
    expect(map.getSource('historical-events')).toBeDefined()
    expect(map.addSource).toHaveBeenCalledTimes(4)
    expect(map.addLayer).toHaveBeenCalledTimes(8)
  })
})
