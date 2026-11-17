import { useEffect, useRef, useState } from 'react'
import { Mic, Pause, Play, Square, Trash2 } from 'lucide-react'
import { courseApi, type Recording, type Story } from '../lib/course-api'
import { errorMessage, useAsync } from '../lib/hooks'
import { canRecord, useRecorder } from '../lib/recorder'
import { dirOf } from '../lib/rtl'
import { useActivityClock } from '../lib/activity'
import { playUrl, speak, stopSpeech } from '../lib/speech'
import { useNav } from '../state/nav'
import { useSettings } from '../state/settings'
import { Button, ErrorNote, IconButton, Loading, Screen, Toggle } from '../components/ui'
import { ItemText, Target } from '../components/Text'
import { PlayButton } from '../components/PlayButton'

export default function StoryReader({ id }: { id: string }) {
  const nav = useNav()
  const { data, error, reload } = useAsync(`story/${id}`, () => courseApi.story(id))
  useEffect(() => () => stopSpeech(), [])
  return (
    <Screen title={data ? (data.kind === 'dialogue' ? 'Dialogue' : 'Story') : 'Story'} onBack={nav.close}>
      <div className="mx-auto w-full max-w-2xl px-4 pb-20 pt-6">
        {!data && !error && <Loading />}
        <ErrorNote error={error} onRetry={reload} />
        {data && <Reader story={data} />}
      </div>
    </Screen>
  )
}

type ShadowPhase = 'listen' | 'record' | 'compare' | 'saving'

function Reader({ story }: { story: Story }) {
  const { pair, settings } = useSettings()
  const lang = pair.target
  const [showAll, setShowAll] = useState(settings.showGloss)
  const [current, setCurrent] = useState<number | null>(null)
  const [playingAll, setPlayingAll] = useState(false)
  const cancel = useRef(false)
  const [shadow, setShadow] = useState<{ line: number; phase: ShadowPhase } | null>(null)
  const [shadowErr, setShadowErr] = useState<string | null>(null)
  const rec = useRecorder()
  const prefix = `story:${story.id}:`
  const recs = useAsync(`recs/${story.id}`, () => courseApi.recordings(undefined, prefix))
  const mine = recs.data ?? []
  const lineRefs = useRef<(HTMLLIElement | null)[]>([])
  // Listening (Play all, shadowing) counts toward the daily goal, logged once when the story closes.
  const clock = useActivityClock('story')

  const pitchOf = (speaker: string) => {
    const v = story.speakers[speaker]?.voice
    return v === 'female' ? 1.12 : v === 'male' ? 0.88 : undefined
  }

  const playAll = async () => {
    if (playingAll) { cancel.current = true; stopSpeech(); return }
    cancel.current = false
    setPlayingAll(true)
    clock.start()
    const start = current ?? 0
    for (let i = start; i < story.lines.length; i++) {
      if (cancel.current) break
      setCurrent(i)
      const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
      lineRefs.current[i]?.scrollIntoView({ block: 'center', behavior: reduce ? 'auto' : 'smooth' })
      await speak(story.lines[i].text, lang, { pitch: pitchOf(story.lines[i].speaker) })
      if (cancel.current) break
      await new Promise((r) => window.setTimeout(r, 450))
    }
    setPlayingAll(false)
    clock.stop()
    if (!cancel.current) setCurrent(null)
  }

  const startShadow = async (i: number) => {
    if (shadow) return
    cancel.current = true
    stopSpeech()
    setPlayingAll(false)
    setShadowErr(null)
    setCurrent(i)
    setShadow({ line: i, phase: 'listen' })
    clock.start()
    await speak(story.lines[i].text, lang, { pitch: pitchOf(story.lines[i].speaker) })
    const ok = await rec.start()
    if (!ok) { setShadow(null); clock.stop(); return }
    setShadow({ line: i, phase: 'record' })
  }

  const stopShadow = async () => {
    if (!shadow) return
    const i = shadow.line
    const take = await rec.stop()
    if (!take) { setShadow(null); clock.stop(); return }
    setShadow({ line: i, phase: 'compare' })
    await speak(story.lines[i].text, lang, { pitch: pitchOf(story.lines[i].speaker) })
    try { await playUrl(take.url) } catch { /* ignore */ }
    setShadow({ line: i, phase: 'saving' })
    try {
      await courseApi.addRecording(take.blob, `${prefix}${i}`, lang, take.seconds)
      recs.reload()
    } catch (e) {
      setShadowErr(`Couldn’t save your recording. ${errorMessage(e)}`)
    } finally {
      URL.revokeObjectURL(take.url)
      setShadow(null)
      clock.stop()
    }
  }

  const removeRec = async (r: Recording, n: number) => {
    if (!window.confirm(`Delete your recording ${n}? This can’t be undone.`)) return
    setShadowErr(null)
    try { await courseApi.deleteRecording(r.id); recs.reload() } catch (e) { setShadowErr(`Couldn’t delete the recording. ${errorMessage(e)}`) }
  }

  const dir = dirOf(lang)
  const latin = dir === 'ltr'

  return (
    <article>
      <header className="mb-8">
        <div dir={dir}>
        <h1 className="font-semibold leading-snug tracking-tight">
          <Target text={story.title} lang={lang} className={latin ? 'font-serif text-[1.9rem]' : 'text-[2rem]'} />
        </h1>
        <p lang={pair.support} className="mt-1 text-[15px] text-ink-2">{story.title_gloss}</p>
        </div>
        <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
          <Button onClick={playAll} variant={playingAll ? 'secondary' : 'primary'} disabled={!!shadow}>
            {playingAll ? <Pause size={18} aria-hidden /> : <Play size={18} fill="currentColor" aria-hidden />}
            {playingAll ? 'Stop' : current !== null ? 'Play from here' : 'Play all'}
          </Button>
          <div className="min-w-[14rem]">
            <Toggle label="Show translations" checked={showAll} onChange={setShowAll} />
          </div>
        </div>
        <ErrorNote error={rec.error ?? shadowErr} />
      </header>

      <ol className="space-y-2">
        {story.lines.map((line, i) => {
          const active = current === i
          const sh = shadow?.line === i ? shadow.phase : null
          const lineRecs = mine.filter((r) => r.ref === `${prefix}${i}`)
          const speaker = story.speakers[line.speaker]?.name ?? line.speaker
          return (
            <li
              key={line.id || i}
              ref={(el) => { lineRefs.current[i] = el }}
              dir={dir}
              className={`rounded-2xl px-3 py-4 transition-colors sm:px-4 ${active ? 'bg-accent-soft' : ''}`}
            >
              {speaker && <p className="mb-1 text-[13px] font-medium text-ink-3">{speaker}</p>}
              <ItemText
                text={line.text}
                tr={line.tr}
                gloss={line.gloss}
                lang={lang}
                supportLang={pair.support}
                size="lg"
                serif={latin}
                showGloss={showAll}
              />
              <div dir="ltr" className={`mt-2 flex items-center gap-1 ${dir === 'rtl' ? 'justify-end' : ''}`}>
                <PlayButton text={line.text} lang={lang} size="sm" pitch={pitchOf(line.speaker)} />
                {canRecord() && (
                  sh === 'record' ? (
                    <Button size="sm" variant="secondary" onClick={stopShadow}>
                      <Square size={14} fill="currentColor" aria-hidden /> Stop
                    </Button>
                  ) : (
                    <Button size="sm" variant="ghost" onClick={() => startShadow(i)} disabled={!!shadow || playingAll} aria-label={`Shadow line ${i + 1}`}>
                      <Mic size={16} aria-hidden /> Shadow
                    </Button>
                  )
                )}
                {sh && sh !== 'record' && (
                  <span className="text-[13px] text-ink-3" role="status">
                    {sh === 'listen' ? 'Listen' : sh === 'compare' ? 'Model, then you' : 'Saving'}
                  </span>
                )}
                {sh === 'record' && <span className="text-[13px] text-danger" role="status">Recording</span>}
              </div>
              {lineRecs.length > 0 && (
                <ul dir="ltr" className={`mt-2 flex flex-wrap gap-2 ${dir === 'rtl' ? 'justify-end' : ''}`}>
                  {lineRecs.map((r, k) => (
                    <li key={r.id} className="flex items-center rounded-full border border-line ps-3 text-[13px] text-ink-2">
                      You {k + 1}
                      <PlayButton url={r.url} size="sm" label={`Play your recording ${k + 1}`} tone="plain" />
                      <IconButton label="Delete recording" size="sm" onClick={() => removeRec(r, k + 1)}><Trash2 size={14} /></IconButton>
                    </li>
                  ))}
                </ul>
              )}
            </li>
          )
        })}
      </ol>
    </article>
  )
}
