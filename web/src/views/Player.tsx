import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { X } from 'lucide-react'
import {
  courseApi, type CompleteRequest, type CompleteResponse, type CourseExercise, type ExerciseSession, type ItemResult,
} from '../lib/course-api'
import { errorMessage, useAsync } from '../lib/hooks'
import { PROMPTS, lenientTr, normSentence, orderText } from '../lib/grading'
import { speak, stopSpeech } from '../lib/speech'
import { useNav, type PlayerSource } from '../state/nav'
import { useSettings } from '../state/settings'
import { Button, ErrorNote, IconButton, Loading, ProgressLine } from '../components/ui'
import { ExerciseBody, Match } from '../components/Exercises'
import { Tgt } from '../components/Text'
import { PlayButton } from '../components/PlayButton'

function loadSession(src: PlayerSource): Promise<ExerciseSession> {
  if (src.type === 'lesson') return courseApi.lessonSession(src.courseId, src.lessonId)
  if (src.type === 'quiz') return courseApi.unitQuiz(src.courseId, src.unitId)
  return courseApi.practice(src.courseId)
}

function complete(src: PlayerSource, body: CompleteRequest): Promise<CompleteResponse> {
  if (src.type === 'lesson') return courseApi.completeLesson(src.courseId, src.lessonId, body)
  if (src.type === 'quiz') return courseApi.completeUnitQuiz(src.courseId, src.unitId, body)
  return courseApi.completePractice(src.courseId, body)
}

const sourceKey = (s: PlayerSource) =>
  s.type === 'lesson' ? `l:${s.courseId}/${s.lessonId}` : s.type === 'quiz' ? `q:${s.courseId}/${s.unitId}` : `p:${s.courseId}`

/** Full-screen lesson / quiz / practice flow. */
export default function Player({ source }: { source: PlayerSource }) {
  const nav = useNav()
  const [attempt, setAttempt] = useState(0)
  const { data, error, reload } = useAsync(`${sourceKey(source)}#${attempt}`, () => loadSession(source))

  useEffect(() => () => stopSpeech(), [])

  if (!data) {
    return (
      <Frame onClose={nav.close} progress={0}>
        <div className="px-4 pt-10">
          {error ? (
            <ErrorNote error={error} onRetry={reload} />
          ) : (
            <Loading label={source.type === 'practice' ? 'Preparing your quiz' : 'Preparing the lesson'} />
          )}
        </div>
      </Frame>
    )
  }
  if (data.exercises.length === 0) {
    return (
      <Frame onClose={nav.close} progress={0}>
        <div className="px-4 pt-16 text-center text-ink-2">There’s nothing to practise here yet.</div>
      </Frame>
    )
  }
  return <Run key={`${data.id}#${attempt}`} session={data} source={source} onRetry={() => setAttempt((a) => a + 1)} />
}

function Frame({ onClose, progress, children, footer }: {
  onClose: () => void
  progress: number
  children: ReactNode
  footer?: ReactNode
}) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => { ref.current?.focus() }, [])
  return (
    <div ref={ref} tabIndex={-1} role="dialog" aria-modal="true" aria-label="Lesson" className="fixed inset-0 z-40 flex flex-col bg-canvas outline-none">
      <div className="pt-safe shrink-0">
        <div className="mx-auto flex h-14 w-full max-w-xl items-center gap-3 px-2 sm:px-4">
          <IconButton label="Close" onClick={onClose}><X size={20} /></IconButton>
          <ProgressLine value={progress} className="h-1.5" label="Progress" />
          <span className="w-2" />
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-xl px-4 pb-8">{children}</div>
      </div>
      {footer}
    </div>
  )
}

interface QueueEntry { ex: CourseExercise; retry: boolean }
type Phase = 'answer' | 'feedback' | 'end'

function Run({ session, source, onRetry }: { session: ExerciseSession; source: PlayerSource; onRetry: () => void }) {
  const nav = useNav()
  const { pair } = useSettings()
  const lang = session.target
  const [queue, setQueue] = useState<QueueEntry[]>(() => session.exercises.map((ex) => ({ ex, retry: false })))
  const [pos, setPos] = useState(0)
  const [answer, setAnswer] = useState('')
  const [matchMissed, setMatchMissed] = useState<string[] | null>(null)
  const [phase, setPhase] = useState<Phase>('answer')
  const [correct, setCorrect] = useState(false)
  const [results, setResults] = useState<ItemResult[]>([])
  const [startedAt] = useState(() => Date.now())
  const [outcome, setOutcome] = useState<{ res?: CompleteResponse; error?: string; sending: boolean } | null>(null)

  const entry = queue[pos]
  const ex = entry?.ex
  const graded = queue.filter((q) => q.ex.kind !== 'intro')
  const progress = phase === 'end' ? 1 : (pos + (phase === 'feedback' ? 1 : 0)) / queue.length

  // Autoplay audio for intro and listen.
  useEffect(() => {
    if (!ex || phase !== 'answer') return
    if ((ex.kind === 'intro' || ex.kind === 'listen') && ex.item) {
      const t = window.setTimeout(() => { void speak(ex.item!.text, lang) }, 250)
      return () => window.clearTimeout(t)
    }
  }, [ex, phase, lang])

  const ready =
    ex?.kind === 'intro' ? true :
    ex?.kind === 'match' ? matchMissed !== null :
    answer.trim().length > 0

  const finish = useCallback(async (all: ItemResult[]) => {
    setPhase('end')
    setOutcome({ sending: true })
    const seconds = Math.round((Date.now() - startedAt) / 1000)
    try {
      const res = await complete(source, { results: all, seconds })
      setOutcome({ res, sending: false })
      nav.bumpData()
    } catch (e) {
      setOutcome({ error: errorMessage(e), sending: false })
    }
  }, [source, startedAt, nav])

  const advance = useCallback((nextResults: ItemResult[], requeue: QueueEntry | null) => {
    stopSpeech()
    const nextQueue = requeue ? [...queue, requeue] : queue
    if (requeue) setQueue(nextQueue)
    if (pos + 1 >= nextQueue.length) {
      void finish(nextResults)
      return
    }
    setPos(pos + 1)
    setAnswer('')
    setMatchMissed(null)
    setPhase('answer')
  }, [queue, pos, finish])

  const check = useCallback(() => {
    if (!ex) return
    if (ex.kind === 'intro') { advance(results, null); return }
    if (!ready) return
    let ok: boolean
    if (ex.kind === 'match') ok = (matchMissed ?? []).length === 0
    else if (ex.kind === 'order') ok = normSentence(orderText(ex, answer)) === normSentence(ex.answer ?? ex.item?.text ?? '')
    else if (ex.kind === 'type_tr') ok = lenientTr(answer) === lenientTr(ex.answer ?? ex.item?.tr ?? '')
    else ok = answer === ex.answer
    setCorrect(ok)
    setPhase('feedback')
    // First attempts count; a retry only re-practises.
    if (!entry.retry) {
      if (ex.kind === 'match') {
        const missed = new Set(matchMissed ?? [])
        setResults((r) => [...r, ...ex.pairs.map((p) => ({ item_id: p.id, correct: !missed.has(p.id) }))])
      } else if (ex.item) {
        setResults((r) => [...r, { item_id: ex.item!.id, correct: ok }])
      }
    }
  }, [ex, entry, ready, answer, matchMissed, advance, results])

  const next = useCallback(() => {
    advance(results, !correct && !entry.retry ? { ex: entry.ex, retry: true } : null)
  }, [advance, results, correct, entry])

  // Keyboard: 1–4 pick a choice, Enter checks / continues.
  useEffect(() => {
    if (phase === 'end' || !ex) return
    const onKey = (e: KeyboardEvent) => {
      const inInput = e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement
      if (e.key === 'Enter') {
        e.preventDefault() // also stops a focused choice button from re-firing
        if (phase === 'feedback') next()
        else check()
        return
      }
      if (inInput || phase !== 'answer') return
      const n = Number(e.key)
      if (n >= 1 && n <= 9 && ['choose_gloss', 'choose_text', 'listen'].includes(ex.kind) && ex.choices[n - 1] !== undefined) {
        setAnswer(ex.choices[n - 1])
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [phase, ex, check, next])

  if (phase === 'end') {
    return (
      <Frame onClose={nav.close} progress={1}>
        <EndScreen session={session} source={source} results={results} outcome={outcome} onDone={nav.close}
          onRetrySend={() => void finish(results)} onRetry={onRetry} />
      </Frame>
    )
  }

  const footer = (
    <div className={`pb-safe shrink-0 border-t ${phase === 'feedback' ? (correct ? 'border-accent/30 bg-accent-soft' : 'border-danger/30 bg-danger-soft') : 'border-line bg-canvas'}`}>
      <div className="mx-auto w-full max-w-xl px-4 py-4">
        {phase === 'feedback' && ex && <Feedback ex={ex} correct={correct} lang={lang} />}
        {phase === 'answer' ? (
          <Button size="lg" block disabled={!ready} onClick={check}>
            {ex?.kind === 'intro' ? 'Continue' : 'Check'}
          </Button>
        ) : (
          <Button size="lg" block onClick={next} autoFocus>Continue</Button>
        )}
      </div>
    </div>
  )

  return (
    <Frame onClose={nav.close} progress={progress} footer={footer}>
      <div key={`${pos}`} className="anim-in pt-4">
        <p className="mb-2 text-center text-[13px] font-medium uppercase tracking-[0.08em] text-ink-3">
          {entry.retry ? 'Once more' : PROMPTS[ex.kind]}
        </p>
        {ex.kind === 'match' ? (
          <Match ex={ex} lang={lang} support={pair.support} locked={phase !== 'answer'} onDone={setMatchMissed} />
        ) : (
          <ExerciseBody ex={ex} lang={lang} support={pair.support} answer={answer} onAnswer={setAnswer} locked={phase !== 'answer'} />
        )}
      </div>
      <span className="sr-only" aria-live="polite">{graded.length ? `${pos + 1} of ${queue.length}` : ''}</span>
    </Frame>
  )
}

function Feedback({ ex, correct, lang }: { ex: CourseExercise; correct: boolean; lang: string }) {
  const it = ex.item
  let right: ReactNode = null
  if (!correct) {
    if (ex.kind === 'choose_gloss') right = ex.answer
    else if (ex.kind === 'type_tr') right = ex.answer ?? it?.tr
    else if (ex.kind === 'match') right = 'Some pairs took a second try.'
    else right = <Tgt lang={lang} className="text-xl">{ex.answer ?? it?.text}</Tgt>
  }
  return (
    <div role="status" className="mb-3 flex items-start gap-3">
      <div className="min-w-0 flex-1">
        <p className={`text-[15px] font-semibold ${correct ? 'text-accent' : 'text-danger'}`}>
          {correct ? 'Correct' : ex.kind === 'match' ? 'Almost' : 'The right answer'}
        </p>
        {right && <div className="mt-0.5 text-ink">{right}</div>}
        {it && ex.kind !== 'match' && (
          <p className="mt-1 text-[13px] text-ink-2">
            <Tgt lang={lang}>{it.text}</Tgt>
            {it.tr && <> · {it.tr}</>} · {it.gloss}
          </p>
        )}
      </div>
      {it && <PlayButton text={it.text} lang={lang} size="sm" />}
    </div>
  )
}

function EndScreen({ session, source, results, outcome, onDone, onRetrySend, onRetry }: {
  session: ExerciseSession
  source: PlayerSource
  results: ItemResult[]
  outcome: { res?: CompleteResponse; error?: string; sending: boolean } | null
  onDone: () => void
  onRetrySend: () => void
  onRetry: () => void
}) {
  const local = results.length ? results.filter((r) => r.correct).length / results.length : 1
  const score = outcome?.res?.score ?? local
  const pct = Math.round(score * 100)
  const failedQuiz = source.type === 'quiz' && outcome?.res && !outcome.res.passed
  const heading =
    source.type === 'quiz' ? (failedQuiz ? 'Not quite yet' : 'Checkpoint passed') :
    source.type === 'practice' ? 'Practice done' : 'Lesson complete'

  return (
    <div className="anim-in flex flex-col items-center pt-14 text-center">
      <p className="text-[13px] uppercase tracking-[0.08em] text-ink-3">{session.title}</p>
      <h2 className="mt-2 text-[1.75rem] font-semibold tracking-tight">{heading}</h2>
      <div className="mt-8 grid w-full max-w-xs grid-cols-2 divide-x divide-line rounded-2xl border border-line bg-surface">
        <div className="px-4 py-5">
          <p className="text-3xl font-semibold tabular-nums">{pct}%</p>
          <p className="mt-1 text-[13px] text-ink-3">score</p>
        </div>
        <div className="px-4 py-5">
          <p className="text-3xl font-semibold tabular-nums">{outcome?.res ? outcome.res.cards_added : '–'}</p>
          <p className="mt-1 text-[13px] text-ink-3">cards added</p>
        </div>
      </div>
      {failedQuiz && <p className="mt-6 max-w-xs text-sm text-ink-2">You need 70% to pass. Review the lessons and try again when you’re ready.</p>}
      {outcome?.sending && <p className="mt-6 text-sm text-ink-3">Saving your progress</p>}
      {outcome?.error && (
        <div className="mt-6 w-full max-w-sm text-start"><ErrorNote error={`Your progress wasn’t saved. ${outcome.error}`} onRetry={onRetrySend} /></div>
      )}
      <div className="mt-10 flex w-full max-w-xs flex-col gap-2">
        <Button size="lg" block onClick={onDone} autoFocus>Continue</Button>
        {failedQuiz && <Button variant="ghost" block onClick={onRetry}>Try again</Button>}
      </div>
    </div>
  )
}
