import { useSyncExternalStore } from 'react'
import { courseApi, type WhoAmI } from './course-api'

// Who is signed in (owner or guest), fetched once per visit. null until known, or when the call fails.

let me: WhoAmI | null = null
let loading: Promise<WhoAmI | null> | null = null
const listeners = new Set<() => void>()

export function getMe(): Promise<WhoAmI | null> {
  loading ??= courseApi.me().then(
    (m) => { me = m; listeners.forEach((fn) => fn()); return m },
    () => { loading = null; return null },
  )
  return loading
}

/** Synchronous: true only once we know this is the owner. */
export const knownOwner = () => me?.owner === true

/** The current user, or null while unknown. */
export function useMe(): WhoAmI | null {
  return useSyncExternalStore(
    (fn) => { listeners.add(fn); void getMe(); return () => { listeners.delete(fn) } },
    () => me,
  )
}
