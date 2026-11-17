import { useEffect, useRef, useState } from 'react'
import { ChevronDown, Mic, Plus, SendHorizontal, Square } from 'lucide-react'
import {
  courseApi, type Item, type Scenario, type TalkMessage, type TalkSession, type TalkSummary,
} from '../lib/course-api'
import { errorMessage, formatElapsed, isStatus, useAsync, useElapsed } from '../lib/hooks'
import { useDictation } from '../lib/dictation'
import { dirOf, languageName } from '../lib/rtl'
import { speak, stopSpeech } from '../lib/speech'
import { useNav } from '../state/nav'
import { useSettings } from '../state/settings'
import { Button, ErrorNote, IconButton, Loading, Screen, SectionLabel, Sheet } from '../components/ui'
import { ItemText, Target } from '../components/Text'
import { PlayButton } from '../components/PlayButton'

export default function TalkChat({ scenarioId }: { scenarioId: string | null }) {
  const nav = useNav()
  const { pair } = useSettings()
  const opening = useRef<Promise<TalkSession> | null>(null)
  const { data, error, reload } = useAsync(`talk|${scenarioId}|${pair.target}|${pair.support}`, () => {
    // Guard against StrictMode's double effect opening two sessions.
    opening.current ??= resumeOrOpen(pair.target, pair.support, scenarioId)
    const p = opening.current
    p.catch(() => { opening.current = null })
    return p
  })
  useEffect(() => () => stopSpeech(), [])

  if (!data) {
    return (
      <Screen title={scenarioId ? 'Role-play' : 'Free conversation'} onBack={nav.close}>
        <div className="mx-auto max-w-2xl px-4 pt-10">
          {error ? <ErrorNote error={error} onRetry={reload} /> : <Loading label="Setting the scene" />}
        </div>
      </Screen>
    )
  }
  return <Chat session={data} />
}

/** The latest conversation for this scenario that hasn't ended, or a new one. */
async function resumeOrOpen(target: string, support: string, scenarioId: string | null): Promise<TalkSession> {
  try {
    const s = await courseApi.latestTalk(target, scenarioId)
    if (!s.ended && (s.scenario?.id ?? null) === scenarioId && s.support === support) return s
  } catch (e) {
    if (!isStatus(e, 404)) throw e
  }
  return courseApi.openTalk({ target, support, scenario_id: scenarioId })
}

const lastIsUser = (ms: TalkMessage[]) => ms.length > 0 && ms[ms.length - 1].role === 'user'

function Chat({ session }: { session: TalkSession }) {
  const nav = useNav()
  const { pair } = useSettings()
  const lang = session.target
  const sc = session.scenario
  const [messages, setMessages] = useState<TalkMessage[]>(session.messages)
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [failed, setFailed] = useState<string | null>(null)
  // Reopening an ended conversation shows its stored summary.
  const [summary, setSummary] = useState<TalkSummary | null>(session.ended ? session.summary : null)
  const [summaryOpen, setSummaryOpen] = useState(session.ended && !!session.summary)
  const [ended, setEnded] = useState(session.ended)
  const [ending, setEnding] = useState(false)
  // A reply that was still being written when the learner left: the server keeps working on it, so
  // check back until it arrives.
  const [awaiting, setAwaiting] = useState(() => !session.ended && lastIsUser(session.messages))
  const elapsed = useElapsed(busy || awaiting)
  const endElapsed = useElapsed(ending)
  const endRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const dictation = useDictation(lang, setInput)

  useEffect(() => {
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    endRef.current?.scrollIntoView({ block: 'end', behavior: reduce ? 'auto' : 'smooth' })
  }, [messages.length, busy])

  useEffect(() => {
    if (!awaiting) return
    const t0 = Date.now()
    const id = window.setInterval(() => {
      courseApi.talk(session.id).then((fresh) => {
        if (!lastIsUser(fresh.messages)) {
          setMessages(fresh.messages)
          setAwaiting(false)
        } else if (Date.now() - t0 > 4 * 60_000) {
          setAwaiting(false)
          setError('No reply came. Send your message again, or end the conversation.')
        }
      }, () => { /* try again on the next tick */ })
    }, 4000)
    return () => window.clearInterval(id)
  }, [awaiting, session.id])

  const send = async (content: string) => {
    const text = content.trim()
    if (!text || busy || awaiting || ended) return
    if (dictation.listening) dictation.stop()
    setError(null); setFailed(null); setInput('')
    setMessages((m) => [...m, { role: 'user', content: text, turn: null, created_at: new Date().toISOString() }])
    setBusy(true)
    try {
      const reply = await courseApi.sayTalk(session.id, text)
      setMessages((m) => [...m, reply])
    } catch (e) {
      setError(errorMessage(e))
      setFailed(text)
      setMessages((m) => m.slice(0, -1))
      setInput(text)
    } finally {
      setBusy(false)
    }
  }

  const end = async () => {
    if (summary) { setSummaryOpen(true); return }
    setEnding(true); setError(null)
    try {
      setSummary(await courseApi.endTalk(session.id))
      setSummaryOpen(true)
      setEnded(true)
      nav.bumpData()
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setEnding(false)
    }
  }

  const insert = (text: string) => {
    setInput((v) => (v ? `${v} ${text}` : text))
    inputRef.current?.focus()
  }

  // Show the scenario opener when the server hasn't put it in the transcript.
  const showOpener = sc && !messages.some((m) => m.role === 'assistant')

  return (
    <Screen
      title={sc ? sc.title : 'Free conversation'}
      onBack={nav.close}
      actions={
        <Button size="sm" variant="secondary" onClick={end} disabled={ending || busy || awaiting || messages.length === 0}>
          {summary ? 'Summary' : ending ? 'Ending' : 'End'}
        </Button>
      }
      footer={
        ended ? (
          <div className="mx-auto flex w-full max-w-2xl items-center justify-between gap-3 px-4 py-3">
            <p className="text-sm text-ink-3">This conversation has ended.</p>
            {summary && <Button size="sm" variant="secondary" onClick={() => setSummaryOpen(true)}>See summary</Button>}
          </div>
        ) : (
        <div className="mx-auto w-full max-w-2xl px-3 py-3 sm:px-4">
          {sc && sc.useful.length > 0 && <Useful items={sc.useful} lang={lang} onInsert={insert} />}
          <ErrorNote error={dictation.error ?? error} onRetry={failed ? () => send(failed) : undefined} />
          <form
            className="mt-2 flex items-end gap-2"
            onSubmit={(e) => { e.preventDefault(); void send(input) }}
          >
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void send(input) }
              }}
              rows={1}
              dir="auto"
              lang={lang}
              aria-label="Message"
              placeholder={`Write in ${languageName(lang)}`}
              title={`Write in ${languageName(lang)}, or in ${languageName(pair.source)} if you’re stuck`}
              className="max-h-32 min-h-11 flex-1 resize-none rounded-2xl border border-line-strong bg-surface px-4 py-2.5 text-[16px] text-ink placeholder:text-[14px] placeholder:text-ink-3 focus:border-accent focus:outline-none"
            />
            {dictation.supported && (
              <IconButton
                label={dictation.listening ? 'Stop dictation' : 'Speak'}
                onClick={dictation.listening ? dictation.stop : dictation.start}
                tone={dictation.listening ? 'solid' : 'plain'}
                className="h-11 w-11"
              >
                {dictation.listening ? <Square size={16} fill="currentColor" /> : <Mic size={20} />}
              </IconButton>
            )}
            <IconButton type="submit" label="Send" tone="solid" disabled={!input.trim() || busy || awaiting} className="h-11 w-11">
              <SendHorizontal size={18} className="rtl:rotate-180" />
            </IconButton>
          </form>
        </div>
        )
      }
    >
      <div className="mx-auto w-full max-w-2xl px-4 pb-6 pt-4">
        {sc && <ScenarioHeader sc={sc} />}

        <ol className="space-y-4">
          {showOpener && (
            <li><AssistantBubble text={sc.opener.text} tr={sc.opener.tr} gloss={sc.opener.gloss} lang={lang} support={session.support} name={sc.persona_name} /></li>
          )}
          {messages.map((m, i) => {
            if (m.role === 'assistant') {
              const t = m.turn
              return (
                <li key={i}>
                  <AssistantBubble text={t?.text ?? m.content} tr={t?.tr ?? null} gloss={t?.gloss ?? null} lang={lang} support={session.support} name={session.scenario?.persona_name} />
                </li>
              )
            }
            const nextTurn = messages[i + 1]?.role === 'assistant' ? messages[i + 1].turn : null
            return (
              <li key={i} className="flex flex-col items-end">
                <div dir="auto" lang={lang} className="max-w-[85%] rounded-3xl rounded-ee-md bg-surface-2 px-4 py-2.5 text-[17px] text-ink">
                  {m.content}
                </div>
                {nextTurn && (nextTurn.better || nextTurn.correction) && (
                  <div className="mt-1.5 max-w-[85%] text-end text-[13px] text-ink-2">
                    {nextTurn.better && (
                      <p>
                        <span className="text-ink-3">Better: </span>
                        <Target text={nextTurn.better} lang={lang} className="text-[15px] text-ink" />
                      </p>
                    )}
                    {nextTurn.correction && <p className="text-ink-3">{nextTurn.correction}</p>}
                  </div>
                )}
              </li>
            )
          })}
          {(busy || awaiting) && <Working label={`Thinking · ${formatElapsed(elapsed)}`} />}
          {ending && <Working label={`Writing your summary · ${formatElapsed(endElapsed)}`} />}
        </ol>
        {messages.length === 0 && !sc && (
          <p className="pt-6 text-center text-sm text-ink-3">Say hello, or ask about anything you’d like to practise.</p>
        )}
        <div ref={endRef} />
      </div>

      {summary && summaryOpen && (
        <SummarySheet summary={summary} lang={lang} support={session.support} onClose={nav.close} onBack={() => setSummaryOpen(false)} />
      )}
    </Screen>
  )
}

function Working({ label }: { label: string }) {
  return (
    <li className="flex items-center gap-3 text-ink-3" role="status">
      <span className="dot-pulse inline-flex gap-1" aria-hidden>
        <span className="h-1.5 w-1.5 rounded-full bg-current" />
        <span className="h-1.5 w-1.5 rounded-full bg-current" />
        <span className="h-1.5 w-1.5 rounded-full bg-current" />
      </span>
      <span className="text-sm">{label}</span>
    </li>
  )
}

function ScenarioHeader({ sc }: { sc: Scenario }) {
  const [open, setOpen] = useState(true)
  return (
    <div className="mb-6 rounded-2xl border border-line bg-surface">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-start"
      >
        <span className="min-w-0">
          <span className="block text-[13px] text-ink-3">Your goal</span>
          <span className="block text-[15px] text-ink">{sc.goal}</span>
        </span>
        <ChevronDown size={18} className={`shrink-0 text-ink-3 transition-transform ${open ? 'rotate-180' : ''}`} aria-hidden />
      </button>
      {open && (
        <div className="border-t border-line px-4 py-3 text-sm text-ink-2">
          <p>{sc.setting}</p>
          {sc.persona && <p className="mt-1 text-ink-3">{sc.persona}</p>}
        </div>
      )}
    </div>
  )
}

function AssistantBubble({ text, tr, gloss, lang, support, name }: {
  text: string
  tr: string | null
  gloss: string | null
  lang: string
  support: string
  name?: string
}) {
  return (
    <div className="flex max-w-[92%] items-start gap-2">
      <div className="min-w-0 rounded-3xl rounded-ss-md border border-line bg-surface px-4 py-3">
        {name && <p className="mb-0.5 text-[12px] text-ink-3">{name}</p>}
        <ItemText text={text} tr={tr} gloss={gloss} lang={lang} supportLang={support} size="md" />
      </div>
      <PlayButton text={text} lang={lang} size="sm" />
    </div>
  )
}

function Useful({ items, lang, onInsert }: { items: Item[]; lang: string; onInsert: (t: string) => void }) {
  const timer = useRef<number | null>(null)
  const long = useRef(false)
  const dir = dirOf(lang)
  return (
    <div className="mb-1">
      <p className="mb-1.5 text-[12px] text-ink-3">Useful phrases · tap to hear, + to use</p>
      <div className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1" dir={dir}>
        {items.map((it) => (
          <span key={it.id} className="flex shrink-0 items-center rounded-full border border-line bg-surface">
            <button
              type="button"
              title={`${it.tr ? `${it.tr} · ` : ''}${it.gloss}`}
              aria-label={`${it.text}, ${it.gloss}. Tap to hear, hold to use.`}
              onPointerDown={() => {
                long.current = false
                timer.current = window.setTimeout(() => { long.current = true; onInsert(it.text) }, 500)
              }}
              onPointerUp={() => { if (timer.current) window.clearTimeout(timer.current) }}
              onPointerLeave={() => { if (timer.current) window.clearTimeout(timer.current) }}
              onClick={() => { if (!long.current) void speak(it.text, lang) }}
              onContextMenu={(e) => e.preventDefault()}
              className="py-1.5 ps-3 pe-1 text-start"
            >
              <Target text={it.text} tr={it.tr} lang={lang} stack className="block text-[15px] leading-tight text-ink" trClassName="text-[11px] text-ink-3" />
              <span dir="ltr" className="block text-[11px] leading-tight text-ink-3">{it.gloss}</span>
            </button>
            <IconButton label={`Use “${it.text}”`} size="sm" onClick={() => onInsert(it.text)}><Plus size={14} /></IconButton>
          </span>
        ))}
      </div>
    </div>
  )
}

function SummarySheet({ summary, lang, support, onClose, onBack }: {
  summary: TalkSummary
  lang: string
  support: string
  onClose: () => void
  onBack: () => void
}) {
  return (
    <Sheet
      label="Conversation summary"
      onClose={onBack}
      footer={
        <div className="flex gap-2">
          <Button variant="secondary" size="lg" onClick={onBack}>Transcript</Button>
          <Button block size="lg" onClick={onClose}>Done</Button>
        </div>
      }
    >
      <h2 className="text-[1.4rem] font-semibold tracking-tight">Nice conversation</h2>
      {summary.went_well && (
        <section className="mt-5">
          <SectionLabel>What went well</SectionLabel>
          <p className="text-[15px] leading-relaxed text-ink-2">{summary.went_well}</p>
        </section>
      )}
      {summary.mistakes.length > 0 && (
        <section className="mt-6">
          <SectionLabel>To polish</SectionLabel>
          <ul className="divide-y divide-line">
            {summary.mistakes.map((m, i) => (
              <li key={i} className="py-3">
                <p className="text-[13px] text-ink-3">You said <Target text={m.you_said} lang={lang} className="text-[15px] text-ink-2 line-through decoration-ink-3/50" /></p>
                <p className="mt-0.5 flex items-center gap-2">
                  <Target text={m.better} lang={lang} className="text-lg text-ink" />
                  <PlayButton text={m.better} lang={lang} size="sm" />
                </p>
                {m.note && <p className="text-[13px] text-ink-2">{m.note}</p>}
              </li>
            ))}
          </ul>
        </section>
      )}
      {summary.new_words.length > 0 && (
        <section className="mt-6">
          <SectionLabel>New words</SectionLabel>
          <ul className="divide-y divide-line">
            {summary.new_words.map((w) => (
              <li key={w.id} className="flex items-center gap-2 py-2.5">
                <div className="min-w-0 flex-1">
                  <ItemText text={w.text} tr={w.tr} gloss={w.gloss} lang={lang} supportLang={support} size="sm" glossMode="show" />
                </div>
                <PlayButton text={w.text} lang={lang} size="sm" />
              </li>
            ))}
          </ul>
        </section>
      )}
      <p className="mt-6 text-sm text-ink-3">
        {summary.cards_added > 0 ? `${summary.cards_added} new card${summary.cards_added === 1 ? '' : 's'} added to your reviews.` : 'No new cards this time.'}
      </p>
    </Sheet>
  )
}
