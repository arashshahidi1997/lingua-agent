import { useEffect, useState } from 'react'
import { api, type Card as Flashcard } from '../lib/api'
import { useLangPair } from '../state/LangPair'
import { isRtl } from '../lib/rtl'
import { Button, Card, ErrorBanner, Loading, Section } from '../components/ui'

const LABELS: { q: number; label: string; tone: 'danger' | 'secondary' | 'primary' }[] = [
  { q: 0, label: '0 blackout', tone: 'danger' },
  { q: 1, label: '1 wrong', tone: 'danger' },
  { q: 2, label: '2 hard miss', tone: 'danger' },
  { q: 3, label: '3 hard but right', tone: 'secondary' },
  { q: 4, label: '4 right', tone: 'primary' },
  { q: 5, label: '5 perfect', tone: 'primary' },
]

export default function Review() {
  const { pair } = useLangPair()
  const [cards, setCards] = useState<Flashcard[] | null>(null)
  const [idx, setIdx] = useState(0)
  const [showBack, setShowBack] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const load = () => {
    setError(null); setShowBack(false); setIdx(0)
    api.cardsDue(pair.target).then(setCards).catch((e) => setError(String(e)))
  }

  useEffect(load, [pair.target])

  const grade = async (q: number) => {
    if (!cards || cards.length === 0) return
    const card = cards[idx % cards.length]
    setBusy(true); setError(null)
    try {
      await api.reviewCard(card.id, q)
      // Drop the just-reviewed card and advance.
      const next = cards.filter((c) => c.id !== card.id)
      setCards(next)
      setShowBack(false)
      setIdx((i) => (next.length === 0 ? 0 : i % next.length))
    } catch (e) {
      setError(String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Section
      title={`Review (${pair.target})`}
      action={
        <a
          href={api.exportAnkiUrl(pair.target)}
          className="rounded-md bg-slate-100 px-3 py-1.5 text-sm font-medium hover:bg-slate-200"
        >
          Export Anki CSV
        </a>
      }
    >
      <ErrorBanner error={error} />
      {!cards && !error && <Loading />}
      {cards && cards.length === 0 && <Card><p className="text-emerald-700">No cards due. ✓</p></Card>}
      {cards && cards.length > 0 && (() => {
        const card = cards[idx % cards.length]
        const targetIsRtl = isRtl(card.target_language)
        return (
          <>
            <div className="text-xs text-slate-500">
              Card <span className="font-mono">{card.id}</span> · interval {card.interval}d ·
              ease {card.ease_factor.toFixed(2)} · reps {card.repetitions} · lapses {card.lapses}
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <Card title="Front">
                <div className="text-2xl" dir={isRtl(card.source_language) ? 'rtl' : 'ltr'}>
                  {card.front}
                </div>
              </Card>
              <Card title="Back">
                {showBack ? (
                  <div className="text-2xl" dir={targetIsRtl ? 'rtl' : 'ltr'}>{card.back}</div>
                ) : (
                  <Button variant="secondary" onClick={() => setShowBack(true)}>Show back</Button>
                )}
              </Card>
            </div>

            {showBack && (
              <Card title="Rate recall">
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-6">
                  {LABELS.map((b) => (
                    <Button key={b.q} variant={b.tone} disabled={busy} onClick={() => grade(b.q)}>
                      {b.label}
                    </Button>
                  ))}
                </div>
              </Card>
            )}

            <p className="text-xs text-slate-500">{cards.length} card{cards.length === 1 ? '' : 's'} remaining in this session.</p>
          </>
        )
      })()}
    </Section>
  )
}
