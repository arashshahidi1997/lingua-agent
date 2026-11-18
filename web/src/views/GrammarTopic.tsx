import { useState, type ReactNode } from 'react'
import { ArrowRight, Check, Lightbulb, X } from 'lucide-react'
import { courseApi, type GrammarExample, type GrammarTask, type GrammarTopic } from '../lib/course-api'
import { useAsync } from '../lib/hooks'
import { Markdown } from '../lib/markdown'
import { newEventId } from '../lib/ids'
import { dirOf } from '../lib/rtl'
import { useMe } from '../lib/me'
import { useNav } from '../state/nav'
import { useSettings } from '../state/settings'
import { Button, ErrorNote, Loading, Screen } from '../components/ui'
import { PlayButton } from '../components/PlayButton'

// Grammar lab, one topic: discover the pattern from examples (guess first), then the rule card, then
// practice (predict a new form, transform a sentence, or choose). Answers are checked by the server, in
// script or transliteration.

type Step = 'discover' | 'rule' | 'practice' | 'done'

export default function GrammarTopicView({ courseId, topicId }: { courseId: string; topicId: string }) {
  const nav = useNav()
  const { data, error, loading, reload } = useAsync(`grammar|${courseId}|${topicId}`, () => courseApi.grammarTopic(courseId, topicId))
  return (
    <Screen title={data?.title ?? 'Grammar'} onBack={nav.close} label="Grammar">
      <div className="mx-auto w-full max-w-2xl px-4 pb-24 pt-6">
        {loading && !data && <Loading />}
        <ErrorNote error={error} onRetry={reload} />
        {data && <Lab topic={data} />}
      </div>
    </Screen>
  )
}

function Lab({ topic }: { topic: GrammarTopic }) {
  const nav = useNav()
  const { pair } = useSettings()
  const lang = pair.target
  const [step, setStep] = useState<Step>(topic.done ? 'rule' : 'discover')
  const [guess, setGuess] = useState<number | null>(null)
  const [results, setResults] = useState<boolean[]>([])
  const [score, setScore] = useState<number | null>(null)
  const [saveErr, setSaveErr] = useState<string | null>(null)
  const [started] = useState(() => Date.now())
  const me = useMe()
  const [status, setStatus] = useState(topic.status)
  const [reviewing, setReviewing] = useState(false)
  const [reviewErr, setReviewErr] = useState<string | null>(null)

  const setReview = async (next: 'draft' | 'reviewed') => {
    setReviewing(true); setReviewErr(null)
    try {
      await courseApi.setGrammarStatus(topic.course_id, topic.id, next)
      setStatus(next)
      nav.bumpData()
    } catch (e) {
      setReviewErr(e instanceof Error ? e.message : String(e))
    } finally {
      setReviewing(false)
    }
  }

  const finish = async (res: boolean[]) => {
    setResults(res)
    setStep('done')
    try {
      const r = await courseApi.grammarComplete(topic.course_id, topic.id, {
        results: res.map((correct, i) => ({ item_id: String(i), correct })),
        seconds: Math.round((Date.now() - started) / 1000),
        event_id: newEventId(),
      })
      setScore(r.score)
      nav.bumpData()
    } catch (e) {
      setSaveErr(e instanceof Error ? e.message : String(e))
    }
  }

  return (
    <div>
      <p className="text-[13px] font-medium uppercase tracking-[0.08em] text-ink-3">
        Grammar lab{status === 'draft' ? ' · draft for your review' : ''}
      </p>
      {me?.owner && <ReviewBar status={status} busy={reviewing} error={reviewErr} onSet={setReview} />}
      <h1 className="mt-1 text-2xl font-semibold tracking-tight">
        {topic.title} {topic.title_fa && <span lang="fa" dir="rtl" className="font-fa font-normal text-ink-3">· {topic.title_fa}</span>}
      </h1>
      <Steps step={step} />

      {step === 'discover' && (
        <section className="mt-6">
          {topic.intro && <p className="text-[16px] text-ink-2">{topic.intro}</p>}
          <ul className="mt-4 divide-y divide-line rounded-2xl bg-surface">
            {topic.examples.map((ex, i) => <ExampleRow key={i} ex={ex} lang={lang} />)}
          </ul>
          <p className="mt-6 text-[17px] font-medium text-ink">{topic.question}</p>
          <div className="mt-3 grid gap-2">
            {topic.choices.map((c, i) => {
              const picked = guess === i
              const tone = guess === null ? 'border-line-strong bg-surface hover:bg-surface-2'
                : i === topic.correct ? 'border-accent bg-accent-soft' : picked ? 'border-danger bg-danger-soft' : 'border-line bg-surface opacity-70'
              return (
                <button key={i} type="button" disabled={guess !== null} onClick={() => setGuess(i)}
                  className={`rounded-2xl border px-4 py-3 text-start text-[15px] text-ink transition-colors ${tone}`}>
                  <Markdown text={c} rtlLang={lang} />
                </button>
              )
            })}
          </div>
          {guess !== null && (
            <div className="mt-4 rounded-2xl bg-surface-2 px-4 py-3 text-[15px] text-ink-2">
              <p className="font-medium text-ink">{guess === topic.correct ? 'You found it.' : 'Not quite.'}</p>
              {topic.why && <Markdown text={topic.why} rtlLang={lang} className="mt-1" />}
              <Button className="mt-3" onClick={() => setStep('rule')}>See the rule <ArrowRight size={16} aria-hidden /></Button>
            </div>
          )}
        </section>
      )}

      {step === 'rule' && (
        <section className="mt-6">
          <div className="rounded-2xl border border-line bg-surface px-5 py-4">
            <p className="mb-2 flex items-center gap-2 text-[13px] font-medium uppercase tracking-[0.08em] text-accent">
              <Lightbulb size={15} aria-hidden /> Rule card
            </p>
            <Markdown text={topic.rule} rtlLang={lang} className="text-[15px] leading-relaxed text-ink-2" />
          </div>
          <Button className="mt-5" onClick={() => setStep('practice')}>
            Practice · {topic.tasks.length} tasks <ArrowRight size={16} aria-hidden />
          </Button>
          {topic.done && <p className="mt-2 text-[13px] text-ink-3">Done before{topic.best_score !== null ? ` · best ${Math.round(topic.best_score * 100)}%` : ''}.</p>}
        </section>
      )}

      {step === 'practice' && <Practice topic={topic} lang={lang} onDone={finish} />}

      {step === 'done' && (
        <section className="mt-8">
          <p className="text-[2rem] font-semibold tabular-nums">
            {results.filter(Boolean).length} / {results.length}
          </p>
          <p className="text-[15px] text-ink-2">
            {score === null && !saveErr ? 'Saving' : 'The rule card stays in your Grammar list.'}
          </p>
          <ErrorNote error={saveErr} />
          <div className="mt-5 flex flex-wrap gap-2">
            <Button variant="secondary" onClick={() => setStep('rule')}>Rule card</Button>
            <Button onClick={nav.close}>Done</Button>
          </div>
        </section>
      )}
    </div>
  )
}

/** Owner only: approve the topic for everyone once you've checked it, or take it back to draft. */
function ReviewBar({ status, busy, error, onSet }: {
  status: 'draft' | 'reviewed'; busy: boolean; error: string | null; onSet: (s: 'draft' | 'reviewed') => void
}) {
  return (
    <div className="mt-3 rounded-2xl border border-line bg-surface-2 px-4 py-3 text-[14px] text-ink-2">
      {status === 'draft' ? (
        <div className="flex flex-wrap items-center gap-3">
          <span className="min-w-0 flex-1">Only you see this topic until you approve it.</span>
          <Button size="sm" disabled={busy} onClick={() => onSet('reviewed')}>Approve for everyone</Button>
        </div>
      ) : (
        <div className="flex flex-wrap items-center gap-3">
          <span className="min-w-0 flex-1">Approved: everyone sees this topic.</span>
          <Button size="sm" variant="ghost" disabled={busy} onClick={() => onSet('draft')}>Back to draft</Button>
        </div>
      )}
      <ErrorNote error={error} />
    </div>
  )
}

function Steps({ step }: { step: Step }) {
  const all: [Step, string][] = [['discover', 'Discover'], ['rule', 'Rule'], ['practice', 'Practice']]
  const at = step === 'done' ? 3 : all.findIndex(([s]) => s === step)
  return (
    <ol className="mt-4 flex gap-4 text-[13px]">
      {all.map(([s, label], i) => (
        <li key={s} className={i === at ? 'font-medium text-accent' : i < at ? 'text-ink-2' : 'text-ink-3'}>
          {i + 1}. {label}
        </li>
      ))}
    </ol>
  )
}

/** The example with its highlighted parts in the accent colour. A highlight that cuts through a word gets a
 *  zero-width joiner on both sides, so Persian letters keep their joined shapes across the cut. */
const LETTER = /[\u0600-\u06FF]/
const ZWJ = '\u200d'

function Highlighted({ text, hl }: { text: string; hl: string[] }) {
  const marks = hl.filter(Boolean)
  const spans: { s: string; mark: boolean }[] = []
  let rest = text
  while (rest && marks.length) {
    let best: { at: number; m: string } | null = null
    for (const m of marks) {
      const at = rest.indexOf(m)
      if (at >= 0 && (best === null || at < best.at || (at === best.at && m.length > best.m.length))) best = { at, m }
    }
    if (!best) break
    if (best.at > 0) spans.push({ s: rest.slice(0, best.at), mark: false })
    spans.push({ s: best.m, mark: true })
    rest = rest.slice(best.at + best.m.length)
  }
  if (rest) spans.push({ s: rest, mark: false })
  const joins = (a: string, b: string) => LETTER.test(a.slice(-1)) && LETTER.test(b[0] ?? '') && a.slice(-1) !== '\u200c'
  const out: ReactNode[] = spans.map((sp, i) => {
    let s = sp.s
    if (i > 0 && joins(spans[i - 1].s, sp.s)) s = ZWJ + s
    if (i < spans.length - 1 && joins(sp.s, spans[i + 1].s)) s = s + ZWJ
    return sp.mark ? <mark key={i} className="rounded-sm bg-accent-soft text-accent">{s}</mark> : <span key={i}>{s}</span>
  })
  return <>{out}</>
}

function ExampleRow({ ex, lang }: { ex: GrammarExample; lang: string }) {
  return (
    <li className="flex items-center gap-3 px-4 py-3">
      <PlayButton text={ex.text.split('←').pop()!.trim()} lang={lang} size="sm" />
      <div className="min-w-0 flex-1">
        <p dir={dirOf(lang)} lang={lang} className="font-fa text-[21px] leading-snug text-ink"><Highlighted text={ex.text} hl={ex.hl} /></p>
        <p className="text-[13px] text-ink-3">{ex.tr} · {ex.gloss}</p>
      </div>
    </li>
  )
}

function Practice({ topic, lang, onDone }: { topic: GrammarTopic; lang: string; onDone: (r: boolean[]) => void }) {
  const [i, setI] = useState(0)
  const [answer, setAnswer] = useState('')
  const [checked, setChecked] = useState<{ correct: boolean; answer: string; answer_tr: string | null } | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [results, setResults] = useState<boolean[]>([])
  const task: GrammarTask = topic.tasks[i]

  const check = async (value = answer) => {
    if (!value.trim()) { setErr('Type an answer first.'); return }
    setBusy(true); setErr(null)
    try {
      const r = await courseApi.grammarCheck(topic.course_id, topic.id, i, value)
      setChecked(r)
      setResults((rs) => [...rs, r.correct])
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  const next = () => {
    if (i + 1 >= topic.tasks.length) { onDone(results); return }
    setAnswer(''); setChecked(null); setErr(null)
    setI(i + 1)
  }

  const dir = dirOf(lang)
  return (
    <section className="mt-6">
      <p className="text-[13px] text-ink-3">Task {i + 1} of {topic.tasks.length}</p>
      <p className="mt-1 text-[17px] font-medium text-ink"><Markdown text={task.prompt} rtlLang={lang} /></p>

      {task.from && (
        <div className="mt-3 rounded-2xl bg-surface px-4 py-3">
          <p dir={dir} lang={lang} className="font-fa text-[21px] text-ink">{task.from.text}</p>
          <p className="text-[13px] text-ink-3">{task.from.tr}{task.from.gloss ? ` · ${task.from.gloss}` : ''}</p>
        </div>
      )}
      {task.given && task.kind !== 'transform' && (
        <p dir={dir} lang={lang} className="font-fa mt-3 text-[21px] text-ink-2">{task.given}</p>
      )}

      {task.kind === 'choose' ? (
        <div className="mt-4 grid gap-2">
          {task.choices.map((c) => {
            const tone = !checked ? 'border-line-strong bg-surface hover:bg-surface-2'
              : c === checked.answer ? 'border-accent bg-accent-soft' : c === answer ? 'border-danger bg-danger-soft' : 'border-line bg-surface opacity-70'
            return (
              <button key={c} type="button" disabled={!!checked || busy} onClick={() => { setAnswer(c); void check(c) }}
                className={`rounded-2xl border px-4 py-3 text-start text-[18px] text-ink ${tone}`}>
                <span dir="auto" className="font-fa">{c}</span>
              </button>
            )
          })}
        </div>
      ) : (
        <form className="mt-4 flex gap-2" onSubmit={(e) => { e.preventDefault(); if (checked) next(); else void check() }}>
          <input
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            disabled={!!checked}
            dir="auto"
            autoComplete="off" autoCapitalize="off" spellCheck={false}
            aria-label="Your answer"
            placeholder={task.mode === 'tr' ? 'in transliteration' : 'in Persian or transliteration'}
            className="h-12 min-w-0 flex-1 rounded-xl border border-line-strong bg-surface px-3 font-fa text-[18px] text-ink outline-none focus:border-accent"
          />
          {!checked && <Button type="submit" disabled={busy}>Check</Button>}
        </form>
      )}
      <ErrorNote error={err} />

      {checked && (
        <div className={`mt-4 rounded-2xl px-4 py-3 ${checked.correct ? 'bg-accent-soft' : 'bg-danger-soft'}`}>
          <p className="flex items-center gap-2 font-medium text-ink">
            {checked.correct ? <Check size={18} className="text-accent" aria-hidden /> : <X size={18} className="text-danger" aria-hidden />}
            {checked.correct ? 'Right' : 'The answer'}
          </p>
          {!checked.correct && (
            <p className="mt-1"><span lang={lang} dir="auto" className="font-fa text-[19px] text-ink">{checked.answer}</span>
              {checked.answer_tr && <span className="text-[14px] text-ink-3"> · {checked.answer_tr}</span>}</p>
          )}
          <Button className="mt-3" onClick={next}>{i + 1 < topic.tasks.length ? 'Next' : 'Finish'} <ArrowRight size={16} aria-hidden /></Button>
        </div>
      )}
    </section>
  )
}
