import { useEffect, useRef, useState } from 'react'
import { api, type Card } from '../lib/api'
import { errorMessage, useAsync } from '../lib/hooks'
import { newEventId } from '../lib/ids'
import { isNetworkError, onSynced, pendingCount, pendingReviewIds, sendOrQueue } from '../lib/offline'
import { dirOf } from '../lib/rtl'
import { useNav } from '../state/nav'
import { loadJson, saveJson, useSettings } from '../state/settings'
import { Button, Empty, ErrorNote, Loading, ProgressLine, Screen } from '../components/ui'
import { Target } from '../components/Text'
import { PlayButton } from '../components/PlayButton'

const RATINGS = [
  { q: 1, label: 'Again', key: '1' },
  { q: 3, label: 'Hard', key: '2' },
  { q: 4, label: 'Good', key: '3' },
  { q: 5, label: 'Easy', key: '4' },
]

const BATCH = 50
const cacheKey = (target: string) => `lingua.dueCards.${target}`

/**
 * Due cards from the server, remembered for offline review. Offline (or when the server can't be reached)
 * the remembered cards are used, minus those with a review still waiting to sync.
 */
async function loadDue(target: string): Promise<{ cards: Card[]; offline: boolean }> {
  try {
    const cards = await api.cardsDue(target, BATCH)
    saveJson(cacheKey(target), cards)
    const pending = pendingReviewIds()
    return { cards: cards.filter((c) => !pending.has(c.id)), offline: false }
  } catch (e) {
    if (!isNetworkError(e)) throw e
    const cached = loadJson<Card[]>(cacheKey(target), [])
    const pending = pendingReviewIds()
    const now = Date.now()
    return {
      cards: (Array.isArray(cached) ? cached : []).filter((c) => !pending.has(c.id) && Date.parse(c.due_at) <= now + 60_000),
      offline: true,
    }
  }
}

/** Due flashcards: front, tap to reveal, then rate. Again and Hard come back at the end of the session. */
export default function Review() {
  const nav = useNav()
  const { pair } = useSettings()
  const initial = useAsync(`due|${pair.target}`, () => loadDue(pair.target))
  const [added, setAdded] = useState<Card[]>([])   // Again / Hard again, and later batches
  const [pos, setPos] = useState(0)
  const [moreError, setMoreError] = useState<string | null>(null)
  const [fetching, setFetching] = useState(false)
  const [wentOffline, setWentOffline] = useState(false)
  const [queued, setQueued] = useState(false)
  const [shown, setShown] = useState(false)
  const [busy, setBusy] = useState(false)
  const [rateError, setRateError] = useState<string | null>(null)
  const [exhausted, setExhausted] = useState(false)
  const [reviewedCount, setReviewedCount] = useState(0)
  const shownAt = useRef(0)
  const settled = useRef(new Set<string>())   // rated Good/Easy this session: not shown again
  const reviewed = useRef(0)

  // Once the queued reviews reach the server, the "saved offline" note has done its job.
  useEffect(() => onSynced(() => {
    if (pendingCount() === 0) { setQueued(false); setWentOffline(false) }
  }), [])

  const queue = initial.data ? [...initial.data.cards, ...added] : null
  const offline = wentOffline || !!initial.data?.offline
  const loadError = initial.error ?? moreError

  const fetchMore = async () => {
    setFetching(true); setMoreError(null)
    try {
      const { cards, offline: off } = await loadDue(pair.target)
      if (off) setWentOffline(true)
      const fresh = off ? [] : cards.filter((c) => !settled.current.has(c.id))
      setAdded((a) => [...a, ...fresh])
      setExhausted(fresh.length === 0)
    } catch (e) {
      setMoreError(errorMessage(e))
    } finally {
      setFetching(false)
    }
  }

  // Leaving midway still updates Today's count.
  const bumpRef = useRef(nav.bumpData)
  useEffect(() => { bumpRef.current = nav.bumpData })
  useEffect(() => () => { if (reviewed.current > 0) bumpRef.current() }, [])

  const card: Card | undefined = queue?.[pos]
  const total = queue?.length ?? 0
  const atEnd = queue !== null && pos >= queue.length

  const rate = async (q: number) => {
    if (!card || busy) return
    setBusy(true); setRateError(null)
    const seconds = shownAt.current ? Math.min(120, Math.round((Date.now() - shownAt.current) / 1000)) : 0
    try {
      const sent = await sendOrQueue({ type: 'review', cardId: card.id, rating: q, eventId: newEventId(), seconds })
      if (sent.queued) { setQueued(true); setWentOffline(true) }
      reviewed.current++
      setReviewedCount((n) => n + 1)
      if (q >= 4) settled.current.add(card.id)
      // Again / Hard: once more at the end of this session.
      else setAdded((a) => [...a, card])
      const nextLen = total + (q >= 4 ? 0 : 1)
      setPos(pos + 1)
      setShown(false)
      shownAt.current = Date.now()
      // Out of cards: ask the server for more (more than one batch was due, or new ones are due by now).
      // Offline, the cards saved on this device are all there is.
      if (pos + 1 >= nextLen && !sent.queued && !offline) void fetchMore()
    } catch (e) {
      setRateError(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!card) return
      if (!shown && (e.key === ' ' || e.key === 'Enter')) { e.preventDefault(); setShown(true); return }
      if (shown) {
        const r = RATINGS.find((x) => x.key === e.key)
        if (r) void rate(r.q)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  const frontLang = card?.source_language ?? pair.source
  const backLang = card?.target_language ?? pair.target
  // Course and Talk cards carry the target side on its own (no transliteration mixed in): speak that.
  const targetSide = card ? (card.text ?? (card.target_language === pair.target ? card.back : card.front)) : ''
  const big = (lang: string) => (dirOf(lang) === 'rtl' ? 'text-[2rem]' : 'text-2xl')
  const finished = atEnd && !fetching && (offline || exhausted || total === 0)

  return (
    <Screen title="Review" onBack={nav.close} backIcon="close">
      <div className="mx-auto flex min-h-full w-full max-w-xl flex-col px-4 pb-8 pt-4">
        {total > 0 && (
          <div className="mb-6 flex items-center gap-3">
            <ProgressLine value={Math.min(pos, total) / total} label="Reviewed" />
            <span className="shrink-0 text-[13px] tabular-nums text-ink-3">{Math.min(pos, total)}/{total}</span>
          </div>
        )}
        {(queue === null || (atEnd && !finished)) && !loadError && <Loading />}
        <ErrorNote error={loadError} onRetry={() => (initial.error ? initial.reload() : void fetchMore())} />
        {(offline || queued) && card && (
          <p className="mb-4 text-center text-[13px] text-ink-3" role="status">
            {queued ? 'Saved offline — will sync.' : 'Offline: reviewing the cards saved on this device.'}
          </p>
        )}
        {finished && !loadError && (
          <div className="pt-8">
            <Empty title={reviewedCount ? 'All caught up' : 'Nothing to review right now'}>
              {reviewedCount
                ? `You reviewed ${reviewedCount} card${reviewedCount === 1 ? '' : 's'}.${queued ? ' Saved offline — will sync.' : ''}`
                : offline ? 'You’re offline, and no due cards are saved on this device.' : 'New cards appear here as you finish lessons.'}
            </Empty>
            <div className="mt-6 flex justify-center"><Button onClick={nav.close}>Done</Button></div>
          </div>
        )}

        {card && (
          <>
            <button
              type="button"
              onClick={() => { shownAt.current ||= Date.now(); setShown(true) }}
              aria-label={shown ? 'Card' : 'Show answer'}
              className="flex min-h-[18rem] flex-1 flex-col items-center justify-center rounded-3xl border border-line bg-surface px-6 py-10 text-center"
            >
              <span lang={frontLang} dir={dirOf(frontLang)} className={`${big(frontLang)} text-ink`}>
                {card.front}
              </span>
              {shown ? (
                <>
                  <span className="my-6 h-px w-16 bg-line" aria-hidden />
                  {card.text ? (
                    <Target text={card.text} tr={card.tr} lang={backLang} stack className={`${big(backLang)} text-ink`}
                      trClassName="mt-1 text-base text-ink-3" />
                  ) : (
                    <span lang={backLang} dir={dirOf(backLang)} className={`${big(backLang)} text-ink`}>{card.back}</span>
                  )}
                </>
              ) : (
                <span className="mt-8 text-[13px] text-ink-3">Tap to reveal</span>
              )}
            </button>
            <div className="mt-3 flex justify-center">
              <PlayButton text={targetSide} lang={pair.target} />
            </div>
            <div className="mt-4"><ErrorNote error={rateError} /></div>
            <div className="mt-4 grid grid-cols-4 gap-2">
              {RATINGS.map((r) => (
                <Button
                  key={r.q}
                  variant={r.q === 4 ? 'primary' : 'secondary'}
                  disabled={!shown || busy}
                  onClick={() => rate(r.q)}
                  className="px-1"
                >
                  {r.label}
                </Button>
              ))}
            </div>
          </>
        )}
      </div>
    </Screen>
  )
}
