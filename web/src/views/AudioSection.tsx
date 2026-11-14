import { useState, type FormEvent } from 'react'
import { FileAudio, Mic, Square, Trash2, Upload } from 'lucide-react'
import { courseApi, type Recording } from '../lib/course-api'
import { errorMessage, formatElapsed, formatTime, useAsync, useElapsed } from '../lib/hooks'
import { canRecord, useRecorder } from '../lib/recorder'
import { useNav } from '../state/nav'
import { useSettings } from '../state/settings'
import { Button, Empty, ErrorNote, Field, IconButton, List, Loading, Panel, Row, SectionLabel, inputCls } from '../components/ui'
import { PlayButton } from '../components/PlayButton'

function recordingLabel(r: Recording): string {
  if (r.ref === 'diary') return 'Speaking diary'
  const m = /^story:[^:]+:(\d+)$/.exec(r.ref)
  if (m) return `Story, line ${Number(m[1]) + 1}`
  return 'Card'
}

export default function AudioSection() {
  return (
    <div className="space-y-10">
      <Recordings />
      <Imported />
    </div>
  )
}

function Recordings() {
  const { pair } = useSettings()
  const { data, error, loading, reload } = useAsync('recordings', () => courseApi.recordings())
  const rec = useRecorder()
  const elapsed = useElapsed(rec.recording)
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const toggle = async () => {
    setErr(null)
    if (!rec.recording) { await rec.start(); return }
    const take = await rec.stop()
    if (!take) return
    setSaving(true)
    try {
      await courseApi.addRecording(take.blob, 'diary', pair.target, take.seconds)
      reload()
    } catch (e) {
      setErr(errorMessage(e))
    } finally {
      setSaving(false)
      URL.revokeObjectURL(take.url)
    }
  }

  const remove = async (id: string) => {
    setErr(null)
    try {
      await courseApi.deleteRecording(id)
      reload()
    } catch (e) {
      setErr(errorMessage(e))
    }
  }

  return (
    <section>
      <SectionLabel>Your recordings</SectionLabel>
      <Panel className="mb-4 flex items-center gap-4 p-4">
        <div className="min-w-0 flex-1">
          <p className="text-[15px] font-medium">Speaking diary</p>
          <p className="text-[13px] text-ink-3">
            {rec.recording ? `Recording · ${formatElapsed(elapsed)}` : saving ? 'Saving' : 'Talk for a minute about your day.'}
          </p>
        </div>
        {canRecord() ? (
          <IconButton label={rec.recording ? 'Stop recording' : 'Record diary entry'} tone="solid" onClick={toggle} disabled={saving}>
            {rec.recording ? <Square size={16} fill="currentColor" /> : <Mic size={20} />}
          </IconButton>
        ) : (
          <span className="text-[13px] text-ink-3">Recording isn’t supported here</span>
        )}
      </Panel>
      <ErrorNote error={rec.error ?? err} />

      {loading && !data && <Loading />}
      {error && !data && <ErrorNote error={error} onRetry={reload} />}
      {data && data.length === 0 && <p className="py-2 text-sm text-ink-3">Recordings from shadowing and your diary show up here.</p>}
      {data && data.length > 0 && (
        <List>
          {data.map((r) => (
            <Row
              key={r.id}
              title={recordingLabel(r)}
              detail={`${new Date(r.created_at).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })}${r.seconds ? ` · ${formatTime(r.seconds)}` : ''}`}
              trailing={
                <span className="flex items-center gap-1">
                  <PlayButton url={r.url} size="sm" label={`Play ${recordingLabel(r)}`} />
                  <IconButton label="Delete recording" size="sm" onClick={() => remove(r.id)}><Trash2 size={16} /></IconButton>
                </span>
              }
            />
          ))}
        </List>
      )}
    </section>
  )
}

function Imported() {
  const { pair } = useSettings()
  const nav = useNav()
  const { data, error, loading, reload } = useAsync('audio', () => courseApi.audio())
  const [showForm, setShowForm] = useState(false)

  return (
    <section>
      <div className="flex items-center justify-between">
        <SectionLabel>Imported audio</SectionLabel>
        {!showForm && (
          <Button size="sm" variant="ghost" onClick={() => setShowForm(true)}><Upload size={16} aria-hidden /> Upload</Button>
        )}
      </div>
      {showForm && <UploadForm lang={pair.target} onDone={() => { setShowForm(false); reload() }} onCancel={() => setShowForm(false)} />}
      {loading && !data && <Loading />}
      {error && !data && (error.startsWith('404') ? null : <ErrorNote error={error} onRetry={reload} />)}
      {data && data.length === 0 && !showForm && (
        <Empty title="No audio yet">
          Upload a podcast episode or a lesson recording you own, with a transcript if you have one.
        </Empty>
      )}
      {data && data.length > 0 && (
        <List>
          {data.map((t) => (
            <Row
              key={t.id}
              icon={<FileAudio size={18} />}
              title={t.title}
              detail={`${t.has_transcript ? 'Transcript' : 'No transcript'} · ${t.source === 'materials' ? 'From materials' : 'Uploaded'}`}
              onClick={() => nav.open({ kind: 'audio', id: t.id })}
            />
          ))}
        </List>
      )}
    </section>
  )
}

function UploadForm({ lang, onDone, onCancel }: { lang: string; onDone: () => void; onCancel: () => void }) {
  const [file, setFile] = useState<File | null>(null)
  const [transcript, setTranscript] = useState<File | null>(null)
  const [title, setTitle] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (!file) return
    setBusy(true); setError(null)
    try {
      await courseApi.uploadAudio(file, { title: title.trim() || undefined, language: lang, transcript })
      onDone()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const fileCls = 'block w-full text-sm text-ink-2 file:me-3 file:rounded-lg file:border file:border-line-strong file:bg-surface file:px-3 file:py-1.5 file:text-sm file:text-ink'

  return (
    <Panel className="mb-4 p-4">
      <form onSubmit={submit} className="space-y-4">
        <Field label="Audio file">
          <input type="file" accept="audio/*,video/mp4" className={fileCls} onChange={(e) => setFile(e.target.files?.[0] ?? null)} required />
        </Field>
        <Field label="Title" hint="Optional. The file name is used otherwise.">
          <input className={inputCls} value={title} onChange={(e) => setTitle(e.target.value)} />
        </Field>
        <Field label="Transcript" hint="Optional: .srt, .vtt or .txt.">
          <input type="file" accept=".srt,.vtt,.txt,text/plain,text/vtt" className={fileCls} onChange={(e) => setTranscript(e.target.files?.[0] ?? null)} />
        </Field>
        <ErrorNote error={error} />
        <div className="flex gap-2">
          <Button type="submit" disabled={!file || busy}>{busy ? 'Uploading' : 'Upload'}</Button>
          <Button variant="ghost" onClick={onCancel}>Cancel</Button>
        </div>
        <p className="text-[13px] text-ink-3">Your files stay on your own server and are never shared.</p>
      </form>
    </Panel>
  )
}
