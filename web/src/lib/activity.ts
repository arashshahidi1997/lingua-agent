import { useCallback, useEffect, useRef } from 'react'
import { logActivity } from './offline'

/**
 * Counts time spent listening or reading (story Play all, the audio player) and logs it toward the daily
 * goal once, when the screen closes. start()/stop() may be called freely; overlapping starts are ignored.
 */
export function useActivityClock(kind: 'story' | 'audio' | 'other') {
  const since = useRef<number | null>(null)
  const total = useRef(0)

  const start = useCallback(() => { since.current ??= Date.now() }, [])
  const stop = useCallback(() => {
    if (since.current !== null) total.current += (Date.now() - since.current) / 1000
    since.current = null
  }, [])

  useEffect(() => () => {
    stop()
    logActivity(total.current, kind)
    total.current = 0
  }, [kind, stop])

  return { start, stop }
}
