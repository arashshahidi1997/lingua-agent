import { useEffect, useRef, useState } from 'react'
import { Check, HelpCircle, RefreshCw, X } from 'lucide-react'
import { courseApi, type Cloze, type ClozeCheck, type ClozeFocus, type ClozeGap } from '../lib/course-api'
import { useAsync } from '../lib/hooks'
import { useActivityClock } from '../lib/activity'
import { dirOf } from '../lib/rtl'
import { useNav } from '../state/nav'
import { useSettings } from '../state/settings'
import { Button, ErrorNote, Loading, Screen, Segmented, Toggle } from '../components/ui'
import { Target } from '../components/Text'
import { PlayButton } from '../components/PlayButton'

// Fill in the blanks over a whole story or dialogue: the gaps follow a grammar focus (verbs, prepositions,
// words, or a mix), you type the missing word (Persian script or transliteration) or pick it from the word
// bank, then check. "New gaps" gives the same text with different blanks.

const FOCUS: { value: ClozeFocus; label: string }[] = [
  { value: 'mixed', label: 'Mixed' },
  { value: 'verbs', label: 'Verbs' },
  { value: 'prepositions', label: 'Prepositions' },
  { value: 'vocab', label: 'Words' },
]

const KIND_HINT: Record<ClozeGap['kind'], string> = {
  verb: 'a verb', preposition: 'a preposition', ra: 'the object marker', vocab: 'a word',
}

export default function ClozeReader({ storyId }: { storyId: string }) {
  const nav = useNav()
  const { pair } = useSettings()
  const [focus, setFocus] = useState<ClozeFocus>('mixed')
  const [seed, setSeed] = useState(0)
  const { data, error, loading, reload } = useAsync(`cloze|${storyId}|${focus}|${seed}`, () => courseApi.cloze(storyId, focus, seed))
  // Time spent here counts toward the daily goal (logged once, when the screen closes).
  const { start } = useActivityClock('story')
  useEffect(() => { start() }, [start])

  return (
    <Screen title={data?.title_gloss || 'Fill the gaps'} onBack={nav.close} label="Fill the gaps">
      <div className="mx-auto w-full max-w-2xl px-4 pb-24 pt-6">
        <p className="text-[13px] font-medium uppercase tracking-[0.08em] text-ink-3">Fill the gaps</p>
        {data && (
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">
            <Target text={data.title} lang={pair.target} /> <span className="font-normal text-ink-3">· {data.title_gloss}</span>
          </h1>
        )}
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <Segmented<ClozeFocus> label="Gaps" value={focus} options={FOCUS} onChange={(f) => { setFocus(f); setSeed(0) }} />
          <Button variant="ghost" onClick={() => setSeed((n) => n + 1)}>
            <RefreshCw size={16} aria-hidden /> New gaps
          </Button>
        </div>
        {loading && !data && <Loading />}
        <ErrorNote error={error} onRetry={reload} />
        {data && <Exercise key={`${focus}|${seed}`} cloze={data} focus={focus} seed={seed} lang={pair.target} />}
      </div>
    </Screen>
  )
}

function Exercise({ cloze, focus, seed, lang }: { cloze: Cloze; focus: ClozeFocus; seed: number; lang: string }) {
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [result, setResult] = useState<ClozeCheck | null>(null)
  const [hints, setHints] = useState<Set<string>>(new Set())
  const [showBank, setShowBank] = useState(false)
  const [showGloss, setShowGloss] = useState(false)
  const [checking, setChecking] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [active, setActive] = useState<string | null>(null)
  const inputs = useRef<Record<string, HTMLInputElement | null>>({})
  const gapIds = cloze.lines.flatMap((l) => l.parts.filter((p) => p.gap).map((p) => p.gap!.id))
  const used = new Set(Object.values(answers))
  const dir = dirOf(lang)

  if (cloze.gap_count === 0) {
    return <p className="mt-8 text-[15px] text-ink-2">This text has nothing to blank for this focus. Try another focus.</p>
  }

  const set = (id: string, v: string) => {
    setAnswers((a) => ({ ...a, [id]: v }))
    if (result) setResult(null)
  }

  const pickFromBank = (word: string) => {
    const target = active && !answers[active] ? active : gapIds.find((id) => !answers[id])
    if (!target) return
    set(target, word)
    const next = gapIds.find((id) => id !== target && !answers[id])
    if (next) { setActive(next); inputs.current[next]?.focus() }
  }

  const check = async () => {
    setChecking(true); setErr(null)
    try {
      setResult(await courseApi.clozeCheck(cloze.story_id, focus, seed, answers))
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
    } finally {
      setChecking(false)
    }
  }

  const right = result ? Object.values(result.correct).filter(Boolean).length : 0

  return (
    <div className="mt-6">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
        <div className="min-w-[13rem]"><Toggle label="Word bank" checked={showBank} onChange={setShowBank} /></div>
        <div className="min-w-[13rem]"><Toggle label="Show translations" checked={showGloss} onChange={setShowGloss} /></div>
      </div>
      <p className="mt-2 text-[13px] text-ink-3">
        Type in Persian or in transliteration. Tap <HelpCircle size={13} className="inline" aria-hidden /> for a hint.
      </p>

      {showBank && (
        <div className="mt-4 flex flex-wrap gap-2 rounded-2xl border border-line bg-surface p-3" dir={dir}>
          {cloze.bank.map((w, i) => (
            <button
              key={`${w}-${i}`}
              type="button"
              onClick={() => pickFromBank(w)}
              className={`rounded-xl border px-3 py-1.5 text-[17px] transition-colors ${used.has(w) ? 'border-line text-ink-3' : 'border-line-strong bg-surface-2 text-ink hover:bg-hover'}`}
            >
              <span lang={lang} className="font-fa">{w}</span>
            </button>
          ))}
        </div>
      )}

      <ol className="mt-6 space-y-5">
        {cloze.lines.map((line, li) => (
          <li key={li} className="rounded-2xl bg-surface px-4 py-3">
            {line.speaker && <p className="mb-1 text-[12px] text-ink-3">{line.speaker}</p>}
            <div className="flex items-start gap-2">
              <p dir={dir} lang={lang} className="font-fa min-w-0 flex-1 text-[20px] leading-[2.4] text-ink">
                {line.parts.map((p, pi) => p.gap ? (
                  <GapInput
                    key={pi}
                    gap={p.gap}
                    value={answers[p.gap.id] ?? ''}
                    onChange={(v) => set(p.gap!.id, v)}
                    onFocus={() => setActive(p.gap!.id)}
                    status={result ? (result.correct[p.gap.id] ? 'right' : 'wrong') : null}
                    hint={hints.has(p.gap.id)}
                    onHint={() => setHints((h) => new Set(h).add(p.gap!.id))}
                    inputRef={(el) => { inputs.current[p.gap!.id] = el }}
                  />
                ) : <span key={pi}>{p.text}</span>)}
              </p>
              <PlayButton text={line.parts.map((p) => p.text ?? p.gap!.answer).join('')} lang={lang} size="sm" />
            </div>
            {showGloss && <p className="mt-1 text-[14px] text-ink-3">{line.gloss}</p>}
          </li>
        ))}
      </ol>

      <div className="sticky bottom-0 mt-8 flex flex-wrap items-center gap-3 border-t border-line bg-canvas py-4">
        <Button onClick={check} disabled={checking}>{checking ? 'Checking' : 'Check'}</Button>
        {result && (
          <p role="status" className="text-[15px] text-ink">
            {right} of {Object.keys(result.correct).length} right
            {right === Object.keys(result.correct).length ? ' — all of them.' : '. The right words are shown under the gaps you missed.'}
          </p>
        )}
        <ErrorNote error={err} />
      </div>
    </div>
  )
}

function GapInput({ gap, value, onChange, onFocus, status, hint, onHint, inputRef }: {
  gap: ClozeGap
  value: string
  onChange: (v: string) => void
  onFocus: () => void
  status: 'right' | 'wrong' | null
  hint: boolean
  onHint: () => void
  inputRef: (el: HTMLInputElement | null) => void
}) {
  const width = `${Math.max(3, gap.answer.length + 1.5)}ch`
  const ring = status === 'right' ? 'border-accent bg-accent-soft' : status === 'wrong' ? 'border-danger bg-danger-soft' : 'border-line-strong bg-surface-2'
  return (
    <span className="relative mx-0.5 inline-flex flex-col items-center align-middle leading-normal">
      <span className="inline-flex items-center gap-0.5">
        <input
          ref={inputRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={onFocus}
          dir="auto"
          autoComplete="off"
          autoCapitalize="off"
          spellCheck={false}
          aria-label={`Gap: ${KIND_HINT[gap.kind]}`}
          style={{ width }}
          className={`h-9 rounded-lg border px-1.5 text-center text-[18px] text-ink outline-none focus:border-accent ${ring}`}
        />
        {status === 'right' && <Check size={14} className="text-accent" aria-label="right" />}
        {status === 'wrong' && <X size={14} className="text-danger" aria-label="wrong" />}
        {!status && (
          <button type="button" onClick={onHint} aria-label="Hint" className="text-ink-3 hover:text-ink">
            <HelpCircle size={14} />
          </button>
        )}
      </span>
      {(hint || status === 'wrong') && (
        <span dir="ltr" className="font-sans text-[12px] leading-tight text-ink-3">
          {status === 'wrong' ? <span lang="fa" className="font-fa text-[15px] text-ink-2">{gap.answer}</span> : (gap.tr ?? KIND_HINT[gap.kind])}
          {status === 'wrong' && gap.tr ? ` · ${gap.tr}` : ''}
        </span>
      )}
    </span>
  )
}
