import { useSyncExternalStore } from 'react'
import { api } from './api'

// Server switches (GET /api/health → features), fetched once per visit.
// Talk is off until a model writes good enough Persian; role-plays then become prompts for your own chatbot.

let talk: boolean | null = null
let loading: Promise<void> | null = null
const listeners = new Set<() => void>()

function load() {
  loading ??= api.health().then(
    (h) => { talk = !!h.features?.talk; listeners.forEach((fn) => fn()) },
    () => { loading = null },
  )
  return loading
}

/** true / false once known; null while loading. */
export function useTalkEnabled(): boolean | null {
  return useSyncExternalStore(
    (fn) => { listeners.add(fn); void load(); return () => { listeners.delete(fn) } },
    () => talk,
  )
}
