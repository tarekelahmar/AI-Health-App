/**
 * Global test setup for Vitest + React Testing Library
 *
 * This file is loaded before every test file (see vite.config.ts `test.setupFiles`)
 * and is responsible for:
 * - extending expect() with jest-dom matchers
 * - cleaning up the DOM after each test
 * - mocking browser APIs that jsdom does not implement or only partially implements
 */

import '@testing-library/jest-dom'
import { afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'

// Ensure React components are unmounted between tests
afterEach(() => {
  cleanup()
})

// --- Browser API shims ---

// matchMedia is used by some components and libraries; jsdom doesn't implement it.
if (!window.matchMedia) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(), // deprecated
      removeListener: vi.fn(), // deprecated
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  })
}

// ResizeObserver is often used by charting/layout libs; provide a minimal stub.
if (!(window as any).ResizeObserver) {
  class ResizeObserver {
    callback: ResizeObserverCallback
    constructor(callback: ResizeObserverCallback) {
      this.callback = callback
    }
    observe() {
      // no-op
    }
    unobserve() {
      // no-op
    }
    disconnect() {
      // no-op
    }
  }
  ;(window as any).ResizeObserver = ResizeObserver
}

// LocalStorage / sessionStorage shims for components that expect them.
const createStorage = () => {
  let store: Record<string, string> = {}
  return {
    getItem(key: string) {
      return key in store ? store[key] : null
    },
    setItem(key: string, value: string) {
      store[key] = value
    },
    removeItem(key: string) {
      delete store[key]
    },
    clear() {
      store = {}
    },
    key(index: number) {
      return Object.keys(store)[index] ?? null
    },
    get length() {
      return Object.keys(store).length
    },
  }
}

if (!('localStorage' in window)) {
  Object.defineProperty(window, 'localStorage', {
    value: createStorage(),
    writable: true,
  })
}

if (!('sessionStorage' in window)) {
  Object.defineProperty(window, 'sessionStorage', {
    value: createStorage(),
    writable: true,
  })
}

// Canvas context stub (used by chart.js when present).
if (!(HTMLCanvasElement.prototype as any).getContext) {
  ;(HTMLCanvasElement.prototype as any).getContext = vi.fn()
}


