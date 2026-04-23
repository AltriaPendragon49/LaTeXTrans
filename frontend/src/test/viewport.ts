import { vi } from "vitest"

function resolveQueryMatch(query: string, width: number) {
  const maxWidthMatch = query.match(/max-width:\s*(\d+)px/)
  if (maxWidthMatch) {
    return width <= Number(maxWidthMatch[1])
  }

  const minWidthMatch = query.match(/min-width:\s*(\d+)px/)
  if (minWidthMatch) {
    return width >= Number(minWidthMatch[1])
  }

  return false
}

export function setViewport(width: number, height = 844) {
  Object.defineProperty(window, "innerWidth", {
    configurable: true,
    writable: true,
    value: width,
  })

  Object.defineProperty(window, "innerHeight", {
    configurable: true,
    writable: true,
    value: height,
  })

  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: resolveQueryMatch(query, width),
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  })

  window.dispatchEvent(new Event("resize"))
}

export function setDesktopViewport() {
  setViewport(1280, 900)
}

export function setMobileViewport() {
  setViewport(390, 844)
}
