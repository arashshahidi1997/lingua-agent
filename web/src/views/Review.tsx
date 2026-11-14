import { useEffect, useState } from 'react'
import { api, type Card } from '../lib/api'
import { errorMessage, useAsync } from '../lib/hooks'
import { dirOf } from '../lib/rtl'
import { useNav } from '../state/nav'
import { useSettings } from '../state/settings'
import { Button, Empty, ErrorNote, Loading, ProgressLine, Screen } from '../components/ui'
import { PlayButton } from '../components/PlayButton'

const RATINGS = [
  { q: 1, label: 'Again', key: '1' },
  { q: 3, label: 'Hard', key: '2' },
  { q: 4, label: 'Good', key: '3' },
  { q: 5, label: 'Easy', key: '4' },
]

/** Due flashcards: front, tap to reveal, then rate. */
export default function Review() {
  const nav = useNav()
  const { pair } = useSettings()
  const { data, error, loading, reload } = useAsync(`due|${pair.target}`, () => api.cardsDue(pair.target))
  const [done, setDone] = useState<string[]>([])
  const [shown, setShown] = useState(false)
  const [busy, setBusy] = useState(false)
  const [rateError, setRateError] = useState<string | null>(null)

  const cards = (data ?? []).filter((c) => !done.includes(c.id))
  const total = data?.length ?? 0
  const card: Card | undefined = cards[0]

  const rate = async (q: number) => {
    if (!card || busy) return
    setBusy(true); setRateError(null)
    try {
      await api.reviewCard(card.id, q)
      setDone((d) => [...d, card.id])
      setShown(false)
      if (cards.length === 1) nav.bumpData()
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
  // Cards can run either way; speak whichever side is in the target language.
  const targetSide = card ? (card.target_language === pair.target ? card.back : card.front) : ''

  return (
    <Screen title="Review" onBack={nav.close} backIcon="close">
      <div className="mx-auto flex min-h-full w-full max-w-xl flex-col px-4 pb-8 pt-4">
        {total > 0 && (
          <div className="mb-6 flex items-center gap-3">
            <ProgressLine value={done.length / total} label="Reviewed" />
            <span className="shrink-0 text-[13px] tabular-nums text-ink-3">{done.length}/{total}</span>
          </div>
        )}
        {loading && !data && <Loading />}
        <ErrorNote error={error} onRetry={reload} />
        {data && !card && (
          <div className="pt-8">
            <Empty title={total ? 'All caught up' : 'Nothing to review right now'}>
              {total ? `You reviewed ${total} card${total === 1 ? '' : 's'}.` : 'New cards appear here as you finish lessons.'}
            </Empty>
            <div className="mt-6 flex justify-center"><Button onClick={nav.close}>Done</Button></div>
          </div>
        )}

        {card && (
          <>
            <button
              type="button"
              onClick={() => setShown(true)}
              aria-label={shown ? 'Card' : 'Show answer'}
              className="flex min-h-[18rem] flex-1 flex-col items-center justify-center rounded-3xl border border-line bg-surface px-6 py-10 text-center"
            >
              <span lang={frontLang} dir={dirOf(frontLang)} className={`${dirOf(frontLang) === 'rtl' ? 'text-[2rem]' : 'text-2xl'} text-ink`}>
                {card.front}
              </span>
              {shown ? (
                <>
                  <span className="my-6 h-px w-16 bg-line" aria-hidden />
                  <span lang={backLang} dir={dirOf(backLang)} className={`${dirOf(backLang) === 'rtl' ? 'text-[2rem]' : 'text-2xl'} text-ink`}>
                    {card.back}
                  </span>
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
