import { useCallback, useEffect, useRef, useState } from 'react'

export interface Take { blob: Blob; seconds: number; url: string }

export function canRecord(): boolean {
  return typeof window !== 'undefined' && 'MediaRecorder' in window && !!navigator.mediaDevices?.getUserMedia
}

/** Microphone recording with MediaRecorder. start() asks for the mic; stop() resolves with the take. */
export function useRecorder() {
  const [recording, setRecording] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const rec = useRef<{ mr: MediaRecorder; stream: MediaStream; chunks: Blob[]; t0: number } | null>(null)
  const pending = useRef<((t: Take | null) => void) | null>(null)

  const release = () => {
    rec.current?.stream.getTracks().forEach((t) => t.stop())
    rec.current = null
  }

  useEffect(() => () => {
    if (rec.current?.mr.state === 'recording') rec.current.mr.stop()
    release()
  }, [])

  const start = useCallback(async (): Promise<boolean> => {
    setError(null)
    if (!canRecord()) {
      setError('Recording is not supported in this browser.')
      return false
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mr = new MediaRecorder(stream)
      const state = { mr, stream, chunks: [] as Blob[], t0: Date.now() }
      mr.ondataavailable = (e) => { if (e.data.size) state.chunks.push(e.data) }
      mr.onstop = () => {
        const blob = new Blob(state.chunks, { type: mr.mimeType || 'audio/webm' })
        const take = { blob, seconds: (Date.now() - state.t0) / 1000, url: URL.createObjectURL(blob) }
        release()
        setRecording(false)
        pending.current?.(take)
        pending.current = null
      }
      rec.current = state
      mr.start()
      setRecording(true)
      return true
    } catch {
      setError('Microphone access was denied or is unavailable.')
      return false
    }
  }, [])

  const stop = useCallback((): Promise<Take | null> => {
    const r = rec.current
    if (!r || r.mr.state !== 'recording') return Promise.resolve(null)
    return new Promise((resolve) => {
      pending.current = resolve
      r.mr.stop()
    })
  }, [])

  return { recording, error, start, stop }
}
