import { useRef, useState } from 'react'
import { Pause, Play, ThumbsDown } from 'lucide-react'
import { courseApi, type VoiceLine, type VoiceSheet } from '../lib/course-api'
import { useAsync } from '../lib/hooks'
import { useNav } from '../state/nav'
import { ErrorNote, Loading, Screen, Segmented, Toggle } from '../components/ui'

// Owner only: listen through every recorded take, sheet by sheet, and mark the bad ones. A take marked bad
// stops being played at once (the other takes, or synthetic speech, fill in); the marks are the re-record
// list for the next recording session.

export default function VoiceReview() {
  const nav = useNav()
  const { data, error, loading, reload } = useAsync('voice-review', () => courseApi.voiceReview())
  const [sheetId, setSheetId] = useState<string | null>(null)
  const [onlyBad, setOnlyBad] = useState(false)
  const [onlyRecorded, setOnlyRecorded] = useState(true)
  const sheets = data ?? []
  const sheet = sheets.find((s) => s.id === sheetId) ?? sheets[0]
  const badCount = sheets.reduce((n, s) => n + s.lines.reduce((m, l) => m + l.takes.filter((t) => t.bad).length, 0), 0)

  return (
    <Screen title="Review your voice" onBack={nav.close} label="Review your voice">
      <div className="mx-auto w-full max-w-2xl px-4 pb-24 pt-6">
        <p className="text-[15px] text-ink-2">
          Listen through your takes and mark the bad ones. A take marked bad is no longer played; the others (or the
          synthetic voice) fill in, and the marked lines are your re-record list.
        </p>
        {loading && !data && <Loading />}
        <ErrorNote error={error} onRetry={reload} />
        {sheet && (
          <>
            <div className="mt-5 flex flex-wrap items-center gap-3">
              <Segmented<string>
                label="Sheet"
                value={sheet.id}
                options={sheets.map((s) => ({ value: s.id, label: `Sheet ${s.id.split('-')[0]}` }))}
                onChange={setSheetId}
              />
            </div>
            <div className="mt-3 flex flex-wrap gap-x-6 gap-y-1">
              <div className="min-w-[14rem]"><Toggle label="Only lines with a bad take" checked={onlyBad} onChange={setOnlyBad} /></div>
              <div className="min-w-[14rem]"><Toggle label="Hide lines not recorded yet" checked={onlyRecorded} onChange={setOnlyRecorded} /></div>
            </div>
            <p className="mt-2 text-[13px] text-ink-3">{badCount} take{badCount === 1 ? '' : 's'} marked bad across all sheets.</p>
            <SheetView key={sheet.id} sheet={sheet} onlyBad={onlyBad} onlyRecorded={onlyRecorded} />
          </>
        )}
      </div>
    </Screen>
  )
}

function SheetView({ sheet, onlyBad, onlyRecorded }: { sheet: VoiceSheet; onlyBad: boolean; onlyRecorded: boolean }) {
  const [lines, setLines] = useState(sheet.lines)
  const [playing, setPlaying] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const audio = useRef<HTMLAudioElement | null>(null)

  const play = (url: string) => {
    audio.current?.pause()
    if (playing === url) { setPlaying(null); return }
    const a = new Audio(url)
    audio.current = a
    setPlaying(url)
    a.onended = () => setPlaying((p) => (p === url ? null : p))
    a.play().catch(() => setPlaying(null))
  }

  const toggle = async (file: string, bad: boolean) => {
    setErr(null)
    setLines((ls) => ls.map((l) => ({ ...l, takes: l.takes.map((t) => (t.file === file ? { ...t, bad } : t)) })))
    try {
      await courseApi.flagTake(file, bad)
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
      setLines((ls) => ls.map((l) => ({ ...l, takes: l.takes.map((t) => (t.file === file ? { ...t, bad: !bad } : t)) })))
    }
  }

  const shown = lines.filter((l) => (!onlyRecorded || l.takes.length > 0) && (!onlyBad || l.takes.some((t) => t.bad)))
  // A section header above the first shown line of each section.
  const headers = shown.map((l, i) => (i === 0 || shown[i - 1].section !== l.section ? l.section : null))
  return (
    <div className="mt-4">
      <ErrorNote error={err} />
      {shown.length === 0 && <p className="mt-6 text-[15px] text-ink-3">Nothing to show with these filters.</p>}
      <ol className="space-y-2">
        {shown.map((l, i) => (
          <li key={l.n}>
            {headers[i] && <p className="mb-1 mt-5 text-[12px] font-medium uppercase tracking-[0.08em] text-ink-3">{headers[i]}</p>}
            <Line line={l} playing={playing} onPlay={play} onToggle={toggle} />
          </li>
        ))}
      </ol>
    </div>
  )
}

function Line({ line, playing, onPlay, onToggle }: {
  line: VoiceLine
  playing: string | null
  onPlay: (url: string) => void
  onToggle: (file: string, bad: boolean) => void
}) {
  const anyBad = line.takes.some((t) => t.bad)
  return (
    <div className={`rounded-2xl border px-4 py-3 ${anyBad ? 'border-danger bg-danger-soft' : 'border-line bg-surface'}`}>
      <div className="flex items-baseline gap-3">
        <span className="w-7 shrink-0 text-[13px] tabular-nums text-ink-3">{line.n}</span>
        <div className="min-w-0 flex-1">
          <p dir="rtl" lang="fa" className="font-fa text-[21px] leading-snug text-ink">{line.text}</p>
          <p className="text-[13px] text-ink-3">{line.tr} · {line.gloss}{line.cue ? ` · say: ${line.cue}` : ''}</p>
        </div>
      </div>
      <div className="mt-2 flex flex-wrap gap-2 ps-10">
        {line.takes.length === 0 && <span className="text-[13px] text-ink-3">No take yet</span>}
        {line.takes.map((t, i) => (
          <span key={t.file} className={`inline-flex items-center gap-1 rounded-xl border px-1.5 py-1 ${t.bad ? 'border-danger' : 'border-line-strong'}`}>
            <button type="button" onClick={() => onPlay(t.url)} aria-label={`Play take ${i + 1}`}
              className="flex h-8 w-8 items-center justify-center rounded-lg text-accent hover:bg-surface-2">
              {playing === t.url ? <Pause size={16} /> : <Play size={16} fill="currentColor" />}
            </button>
            <span className="text-[12px] tabular-nums text-ink-3" title={t.source}>{i + 1}</span>
            <button type="button" onClick={() => onToggle(t.file, !t.bad)} aria-pressed={t.bad}
              aria-label={t.bad ? `Take ${i + 1} is marked bad; mark it good` : `Mark take ${i + 1} bad`}
              className={`flex h-8 items-center gap-1 rounded-lg px-2 text-[12px] ${t.bad ? 'bg-danger text-white' : 'text-ink-3 hover:bg-surface-2'}`}>
              <ThumbsDown size={14} aria-hidden /> {t.bad ? 'Bad' : ''}
            </button>
          </span>
        ))}
      </div>
    </div>
  )
}
