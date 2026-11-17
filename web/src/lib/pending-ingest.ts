import { useSyncExternalStore } from 'react'
import { api, type IngestSummary } from './api'
import { errorMessage } from './hooks'

// "Make a lesson" can take minutes with a local model. The request lives here, outside the view, so
// leaving Add text and coming back still shows it is being made (and then its result).

export interface IngestJob {
  title: string
  startedAt: number
  done: boolean
  result: IngestSummary | null
  error: string | null
}

let job: IngestJob | null = null
const listeners = new Set<() => void>()
const emit = () => listeners.forEach((fn) => fn())

export function startIngest(body: Parameters<typeof api.ingestText>[0], onDone?: () => void) {
  if (job && !job.done) return
  const mine: IngestJob = { title: body.title, startedAt: Date.now(), done: false, result: null, error: null }
  job = mine
  emit()
  api.ingestText(body).then(
    (result) => { if (job === mine) { job = { ...mine, done: true, result }; emit() }; onDone?.() },
    (e) => { if (job === mine) { job = { ...mine, done: true, error: errorMessage(e) }; emit() } },
  )
}

export function clearIngest() {
  if (job && !job.done) return
  job = null
  emit()
}

export function useIngestJob(): IngestJob | null {
  return useSyncExternalStore(
    (fn) => { listeners.add(fn); return () => { listeners.delete(fn) } },
    () => job,
  )
}
