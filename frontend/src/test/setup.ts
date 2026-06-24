// Extends Vitest's `expect` with jest-dom matchers (toBeInTheDocument, …) and
// keeps each test isolated by clearing the DOM and localStorage afterwards.
import '@testing-library/jest-dom/vitest'
import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'

// jsdom doesn't implement Element.prototype.scrollTo; ChatWindow auto-scrolls
// on new messages, so provide a no-op to avoid runtime errors under test.
if (!Element.prototype.scrollTo) {
  Element.prototype.scrollTo = () => {}
}

// A small in-memory localStorage so the app's bare `localStorage` calls work
// consistently under the jsdom environment (where it isn't always exposed as a
// global) and stay isolated between tests.
class MemoryStorage implements Storage {
  private store = new Map<string, string>()
  get length(): number {
    return this.store.size
  }
  clear(): void {
    this.store.clear()
  }
  getItem(key: string): string | null {
    return this.store.has(key) ? (this.store.get(key) as string) : null
  }
  key(index: number): string | null {
    return Array.from(this.store.keys())[index] ?? null
  }
  removeItem(key: string): void {
    this.store.delete(key)
  }
  setItem(key: string, value: string): void {
    this.store.set(key, String(value))
  }
}

Object.defineProperty(globalThis, 'localStorage', {
  value: new MemoryStorage(),
  configurable: true,
  writable: true,
})

afterEach(() => {
  cleanup()
  localStorage.clear()
})
