import { useCallback, useEffect, useRef, useState } from 'react'

export function errorMessage(e: unknown): string {
  if (e instanceof Error) return e.message
  return String(e)
}

/** Friendly error: hides HTTP noise for the common cases. */
export function friendlyError(error: string): string {
  if (error.startsWith('404')) return 'Not found — it may have been deleted.'
  if (error.startsWith('501')) return 'This isn’t set up yet.'
  if (/failed to fetch|networkerror|load failed|network error/i.test(error)) {
    return 'Can’t reach the app — check your connection and that Tailscale is on.'
  }
  return error.replace(/^\d{3}\s+/, '')
}

/** True when an error message came from an HTTP status (our fetch wrappers prefix it). */
export function isStatus(e: unknown, status: number): boolean {
  return errorMessage(e).startsWith(`${status} `)
}

interface AsyncState<T> { key: string | null; nonce: number; data?: T; error?: string }

/**
 * Load data for `key` (null = don't load). Re-runs when the key changes or on reload().
 * Keeps the previous data while reloading the same key.
 */
export function useAsync<T>(key: string | null, fn: () => Promise<T>) {
  const fnRef = useRef(fn)
  useEffect(() => { fnRef.current = fn })
  const [nonce, setNonce] = useState(0)
  const [state, setState] = useState<AsyncState<T>>({ key: null, nonce: -1 })

  useEffect(() => {
    if (key === null) return
    let alive = true
    fnRef.current().then(
      (data) => { if (alive) setState({ key, nonce, data }) },
      (e) => { if (alive) setState({ key, nonce, error: errorMessage(e) }) },
    )
    return () => { alive = false }
  }, [key, nonce])

  const reload = useCallback(() => setNonce((n) => n + 1), [])
  const sameKey = state.key === key
  return {
    data: sameKey ? state.data : undefined,
    error: sameKey && state.nonce === nonce ? state.error : undefined,
    loading: key !== null && (!sameKey || state.nonce !== nonce),
    reload,
    setData: (d: T) => setState({ key, nonce, data: d }),
  }
}

/** Seconds elapsed since `running` became true; 0 when not running. */
export function useElapsed(running: boolean): number {
  const [start, setStart] = useState<number | null>(null)
  const [now, setNow] = useState(0)
  useEffect(() => {
    if (!running) return
    const t0 = Date.now()
    const id = window.setInterval(() => { setStart(t0); setNow(Date.now()) }, 1000)
    return () => { window.clearInterval(id); setStart(null) }
  }, [running])
  if (!running || start === null) return 0
  return Math.max(0, Math.round((now - start) / 1000))
}

/** Seconds since the timestamp `t0` (ms), ticking each second; 0 when null. */
export function useSecondsSince(t0: number | null): number {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    if (t0 === null) return
    const id = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(id)
  }, [t0])
  return t0 === null ? 0 : Math.max(0, Math.round((now - t0) / 1000))
}

export function formatElapsed(s: number): string {
  const m = Math.floor(s / 60)
  const r = s % 60
  return m ? `${m}:${String(r).padStart(2, '0')}` : `${r}s`
}

export function formatTime(s: number): string {
  if (!Number.isFinite(s)) return '0:00'
  const m = Math.floor(s / 60)
  const r = Math.floor(s % 60)
  return `${m}:${String(r).padStart(2, '0')}`
}

/** Escape / outside-click handling for small popovers. */
export function useDismiss(open: boolean, close: () => void) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!open) return
    const onDown = (e: PointerEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) close()
    }
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') close() }
    document.addEventListener('pointerdown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('pointerdown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open, close])
  return ref
}
