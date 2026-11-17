// Offline queue for progress writes: lesson / quiz / practice completions, card reviews and activity time.
//
// When one of these POSTs fails because the network is down, the call is stored (with its event_id, so
// the server can drop a replay it has already seen) in localStorage and replayed in order when the app
// is back online (the `online` event, and at app start). Everything else still fails loudly.

import { api } from './api'
import { courseApi, type CompleteRequest } from './course-api'
import { newEventId } from './ids'

export type QueuedOp =
  | { type: 'lesson'; courseId: string; lessonId: string; body: CompleteRequest }
  | { type: 'quiz'; courseId: string; unitId: string; body: CompleteRequest }
  | { type: 'practice'; courseId: string; body: CompleteRequest }
  | { type: 'review'; cardId: string; rating: number; eventId: string; seconds: number }
  | { type: 'activity'; seconds: number; kind: 'story' | 'audio' | 'review' | 'other'; eventId: string }

interface Entry { op: QueuedOp; at: number }

const KEY = 'lingua.offlineQueue'

function load(): Entry[] {
  try {
    const raw = window.localStorage.getItem(KEY)
    const parsed: unknown = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? (parsed as Entry[]) : []
  } catch {
    return []
  }
}

function save(entries: Entry[]) {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(entries))
  } catch {
    // storage unavailable: the entry lives only in memory for this visit
  }
}

let memory: Entry[] | null = null
const entries = () => (memory ??= load())

// ---- subscribers (pending count, synced) ------------------------------------------

type Listener = () => void
const listeners = new Set<Listener>()
const syncedListeners = new Set<Listener>()

export function subscribeQueue(fn: Listener): () => void {
  listeners.add(fn)
  return () => { listeners.delete(fn) }
}

/** Called after queued items reached the server, so views can refetch. */
export function onSynced(fn: Listener): () => void {
  syncedListeners.add(fn)
  return () => { syncedListeners.delete(fn) }
}

export const pendingCount = () => entries().length

/** Card ids with a review waiting to sync (so offline review doesn't show them again). */
export function pendingReviewIds(): Set<string> {
  return new Set(entries().flatMap((e) => (e.op.type === 'review' ? [e.op.cardId] : [])))
}

function set(next: Entry[]) {
  memory = next
  save(next)
  listeners.forEach((fn) => fn())
}

export function enqueue(op: QueuedOp) {
  set([...entries(), { op, at: Date.now() }])
}

/** True when an error means "no network" rather than "the server said no". */
export function isNetworkError(e: unknown): boolean {
  if (typeof navigator !== 'undefined' && navigator.onLine === false) return true
  return e instanceof TypeError
}

// ---- sending ---------------------------------------------------------------------

function send(op: QueuedOp): Promise<unknown> {
  switch (op.type) {
    case 'lesson': return courseApi.completeLesson(op.courseId, op.lessonId, op.body)
    case 'quiz': return courseApi.completeUnitQuiz(op.courseId, op.unitId, op.body)
    case 'practice': return courseApi.completePractice(op.courseId, op.body)
    case 'review': return api.reviewCard(op.cardId, op.rating, op.eventId, op.seconds)
    case 'activity': return courseApi.logActivity(op.seconds, op.kind, op.eventId)
  }
}

export type Sent<T> = { queued: false; data: T } | { queued: true }

/**
 * Send now; when the network is down, queue it and resolve `{ queued: true }`. Server errors still throw.
 * Ops with a body need an event_id there; pass ops built with one (see `completeOp`).
 */
export async function sendOrQueue<T>(op: QueuedOp): Promise<Sent<T>> {
  // Keep order: older items go first. If they can't, this one waits behind them.
  if (pendingCount() > 0) {
    await flush()
    if (pendingCount() > 0) {
      enqueue(op)
      return { queued: true }
    }
  }
  try {
    return { queued: false, data: (await send(op)) as T }
  } catch (e) {
    if (!isNetworkError(e)) throw e
    enqueue(op)
    return { queued: true }
  }
}

export function completeOp(
  src: { type: 'lesson'; courseId: string; lessonId: string } | { type: 'quiz'; courseId: string; unitId: string } | { type: 'practice'; courseId: string },
  body: Omit<CompleteRequest, 'event_id'>,
  eventId: string,
): QueuedOp {
  const b: CompleteRequest = { ...body, event_id: eventId }
  if (src.type === 'lesson') return { type: 'lesson', courseId: src.courseId, lessonId: src.lessonId, body: b }
  if (src.type === 'quiz') return { type: 'quiz', courseId: src.courseId, unitId: src.unitId, body: b }
  return { type: 'practice', courseId: src.courseId, body: b }
}

/** Time toward the daily goal outside lessons; queued like the rest when offline. Ignores a few seconds. */
export function logActivity(seconds: number, kind: 'story' | 'audio' | 'review' | 'other') {
  const s = Math.round(seconds)
  if (s < 5) return
  void sendOrQueue({ type: 'activity', seconds: Math.min(s, 4 * 60 * 60), kind, eventId: newEventId() }).catch(() => {
    // a server error on a time log isn't worth bothering the learner with
  })
}

// ---- replay ------------------------------------------------------------------------

let flushing: Promise<void> | null = null

/** Replay queued items in order. Stops at the first network failure; drops items the server refuses. */
export function flush(): Promise<void> {
  flushing ??= (async () => {
    let sent = 0
    try {
      while (entries().length) {
        const head = entries()[0]
        try {
          await send(head.op)
          sent++
        } catch (e) {
          if (isNetworkError(e)) break
          const msg = e instanceof Error ? e.message : String(e)
          // 5xx: the server is up but unwell; try again later. 4xx: it will never succeed, drop it.
          if (/^5\d\d /.test(msg)) break
        }
        set(entries().filter((x) => x !== head))
      }
    } finally {
      flushing = null
      if (sent) syncedListeners.forEach((fn) => fn())
    }
  })()
  return flushing
}

let started = false

/** Replay at app start and whenever the browser comes back online. */
export function startOfflineSync() {
  if (started || typeof window === 'undefined') return
  started = true
  window.addEventListener('online', () => { void flush() })
  if (pendingCount() > 0) void flush()
}
