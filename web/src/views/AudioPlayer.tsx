import { useEffect, useRef, useState } from 'react'
import { Pause, Play, Repeat, RotateCcw, Trash2 } from 'lucide-react'
import { courseApi, type AudioTrackDetail } from '../lib/course-api'
import { errorMessage, formatTime, isStatus, useAsync } from '../lib/hooks'
import { dirOf } from '../lib/rtl'
import { useActivityClock } from '../lib/activity'
import { useMe } from '../lib/me'
import { stopSpeech } from '../lib/speech'
import { useNav } from '../state/nav'
import { useSettings } from '../state/settings'
import { Button, Empty, ErrorNote, IconButton, Loading, Screen, Segmented, Toggle } from '../components/ui'
import { Target } from '../components/Text'

/** Imported audio with a cue list synced to playback. */
export default function AudioPlayer({ id }: { id: string }) {
  const nav = useNav()
  const { data, error, reload, setData } = useAsync(`audio/${id}`, () => courseApi.audioTrack(id))
  const [delError, setDelError] = useState<string | null>(null)

  const remove = async () => {
    if (!window.confirm('Delete this audio from your library? The file is removed and this can’t be undone.')) return
    setDelError(null)
    try {
      await courseApi.deleteAudio(id)
      nav.bumpData()
      nav.close()
    } catch (e) {
      setDelError(`Couldn’t delete the audio. ${errorMessage(e)}`)
    }
  }

  return (
    <Screen
      title={data?.title ?? 'Audio'}
      onBack={nav.close}
      actions={data && <IconButton label="Delete audio" onClick={remove}><Trash2 size={18} /></IconButton>}
    >
      <div className="mx-auto w-full max-w-2xl px-4 pb-16 pt-4">
        {!data && !error && <Loading />}
        <ErrorNote error={error} onRetry={reload} />
        {delError && <div className="mb-4"><ErrorNote error={delError} /></div>}
        {data && <Track track={data} onTranscribed={setData} />}
      </div>
    </Screen>
  )
}

function Track({ track, onTranscribed }: { track: AudioTrackDetail; onTranscribed: (t: AudioTrackDetail) => void }) {
  const { settings } = useSettings()
  const audio = useRef<HTMLAudioElement>(null)
  const listRef = useRef<HTMLOListElement>(null)
  const [time, setTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [rate, setRate] = useState<'0.75' | '1'>(settings.rate === 0.75 ? '0.75' : '1')
  const [loop, setLoop] = useState(false)
  const [transcribing, setTranscribing] = useState(false)
  const [tErr, setTErr] = useState<string | null>(null)
  const [showGloss, setShowGloss] = useState(settings.showGloss)
  const me = useMe()
  const clock = useActivityClock('audio')
  const hasGloss = track.cues.some((c) => c.gloss)

  const cues = track.cues
  const current = cues.findIndex((c) => time >= c.start && time < c.end)
  const loopCue = useRef<number>(-1)

  useEffect(() => { if (audio.current) audio.current.playbackRate = Number(rate) }, [rate])

  // Keep the current cue in view.
  useEffect(() => {
    if (current < 0 || !listRef.current) return
    const el = listRef.current.children[current] as HTMLElement | undefined
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    el?.scrollIntoView({ block: 'nearest', behavior: reduce ? 'auto' : 'smooth' })
  }, [current])

  const onTime = () => {
    const a = audio.current
    if (!a) return
    if (loop) {
      if (loopCue.current < 0) loopCue.current = cues.findIndex((c) => a.currentTime >= c.start && a.currentTime < c.end)
      const c = cues[loopCue.current]
      if (c && a.currentTime >= c.end) a.currentTime = c.start
    }
    setTime(a.currentTime)
  }

  const toggle = () => {
    const a = audio.current
    if (!a) return
    if (a.paused) { stopSpeech(); void a.play() } else a.pause()
  }

  const seek = (t: number) => {
    const a = audio.current
    if (!a) return
    a.currentTime = t
    setTime(t)
    if (loop) loopCue.current = cues.findIndex((c) => t >= c.start && t < c.end)
    if (a.paused) void a.play()
  }

  const transcribe = async () => {
    setTranscribing(true); setTErr(null)
    try {
      onTranscribed(await courseApi.transcribeAudio(track.id))
    } catch (e) {
      setTErr(isStatus(e, 501)
        ? 'Transcription isn’t set up yet. You can upload a transcript (.srt, .vtt or .txt) with the audio instead.'
        : errorMessage(e))
    } finally {
      setTranscribing(false)
    }
  }

  const dir = dirOf(track.language)

  return (
    <div>
      <audio
        ref={audio}
        src={track.url}
        preload="metadata"
        onTimeUpdate={onTime}
        onLoadedMetadata={(e) => { setDuration(e.currentTarget.duration); e.currentTarget.playbackRate = Number(rate) }}
        onPlay={() => { setPlaying(true); clock.start() }}
        onPause={() => { setPlaying(false); clock.stop() }}
        onEnded={() => { setPlaying(false); clock.stop() }}
      />

      {/* transport */}
      <div className="sticky top-0 z-10 -mx-4 border-b border-line bg-canvas px-4 pb-4 pt-2">
        <div className="flex items-center gap-3">
          <IconButton label={playing ? 'Pause' : 'Play'} tone="solid" onClick={toggle} className="h-12 w-12">
            {playing ? <Pause size={20} fill="currentColor" /> : <Play size={20} fill="currentColor" className="ms-0.5" />}
          </IconButton>
          <div className="min-w-0 flex-1">
            <input
              type="range"
              min={0}
              max={duration || 0}
              step={0.1}
              value={Math.min(time, duration || 0)}
              onChange={(e) => seek(Number(e.target.value))}
              aria-label="Seek"
              className="w-full accent-[var(--accent)]"
            />
            <div className="flex justify-between text-[12px] tabular-nums text-ink-3">
              <span>{formatTime(time)}</span>
              <span>{formatTime(duration)}</span>
            </div>
          </div>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Segmented label="Speed" value={rate} onChange={setRate} options={[{ value: '0.75', label: '0.75×' }, { value: '1', label: '1×' }]} />
          <button
            type="button"
            aria-pressed={loop}
            onClick={() => { loopCue.current = -1; setLoop((l) => !l) }}
            disabled={!cues.length}
            className={`inline-flex h-10 items-center gap-1.5 rounded-xl px-3 text-sm transition-colors disabled:opacity-40 ${loop ? 'bg-accent-soft font-medium text-accent' : 'text-ink-2 hover:bg-surface-2'}`}
          >
            <Repeat size={16} aria-hidden /> Loop line
          </button>
          <IconButton label="Back 5 seconds" onClick={() => seek(Math.max(0, time - 5))}><RotateCcw size={18} /></IconButton>
          {hasGloss && (
            <div className="ms-auto min-w-[13rem]"><Toggle label="Show translations" checked={showGloss} onChange={setShowGloss} /></div>
          )}
        </div>
      </div>

      {cues.length === 0 ? (
        <div className="pt-6">
          {me?.owner ? (
            <Empty
              title="No transcript yet"
              action={<Button variant="secondary" onClick={transcribe} disabled={transcribing}>{transcribing ? 'Transcribing. This can take a while.' : 'Transcribe'}</Button>}
            >
              Make one to follow along line by line.
            </Empty>
          ) : (
            <Empty title="No transcript yet">Upload the audio again with a transcript (.srt, .vtt or .txt) to follow along line by line.</Empty>
          )}
          <div className="mt-4"><ErrorNote error={tErr} /></div>
        </div>
      ) : (
        <ol ref={listRef} className="mt-2 divide-y divide-line">
          {cues.map((c, i) => {
            const active = i === current
            return (
              <li key={i}>
                <button
                  type="button"
                  onClick={() => seek(c.start)}
                  aria-current={active ? 'true' : undefined}
                  className={`flex w-full gap-3 rounded-xl px-2 py-3 text-start transition-colors ${active ? 'bg-accent-soft' : 'hover:bg-surface-2/70'}`}
                >
                  <span className="w-10 shrink-0 pt-1 text-[12px] tabular-nums text-ink-3">{formatTime(c.start)}</span>
                  <span className="min-w-0 flex-1">
                    <span dir={dir} className="block">
                      <Target text={c.text} tr={c.tr} lang={track.language} stack
                        className={`${dir === 'rtl' ? 'text-xl' : 'font-serif text-lg'} ${active ? 'text-ink' : 'text-ink-2'}`}
                        trClassName="mt-0.5 text-[13px] text-ink-3" />
                    </span>
                    {c.gloss && showGloss && <span className="mt-0.5 block text-[13px] text-ink-2">{c.gloss}</span>}
                  </span>
                </button>
              </li>
            )
          })}
        </ol>
      )}
    </div>
  )
}
