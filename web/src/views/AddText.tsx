import { useState, type FormEvent } from 'react'
import { ArrowLeft } from 'lucide-react'
import { api, type IngestSummary } from '../lib/api'
import { errorMessage, formatElapsed, useElapsed } from '../lib/hooks'
import { dirOf, languageName } from '../lib/rtl'
import { useNav } from '../state/nav'
import { useSettings } from '../state/settings'
import { Button, ErrorNote, Field, Panel, Spinner, inputCls } from '../components/ui'

const LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']

/** "+ Add": paste a text and turn it into a lesson (the old Ingest view). */
export default function AddText({ onBack }: { onBack: () => void }) {
  const { pair } = useSettings()
  const nav = useNav()
  const [title, setTitle] = useState('')
  const [text, setText] = useState('')
  const [level, setLevel] = useState('A1')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [made, setMade] = useState<IngestSummary | null>(null)
  const elapsed = useElapsed(busy)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true); setError(null); setMade(null)
    try {
      const res = await api.ingestText({
        text: text.trim(),
        title: title.trim(),
        source_language: pair.source,
        target_language: pair.target,
        support_language: pair.support,
        cefr_level: level,
      })
      setMade(res)
      setText(''); setTitle('')
      nav.bumpData()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <button type="button" onClick={onBack} className="mb-4 inline-flex items-center gap-1.5 rounded-lg text-sm text-ink-2 hover:text-ink">
        <ArrowLeft size={16} className="rtl:rotate-180" aria-hidden /> Library
      </button>
      <h2 className="text-xl font-semibold tracking-tight">Add your own text</h2>
      <p className="mt-1 text-[15px] text-ink-2">
        Paste a {languageName(pair.target)} text: an article, a song you own, a dialogue from a course book.
        It becomes a lesson with vocabulary, grammar notes and flashcards.
      </p>

      {made && (
        <Panel className="mt-6 p-4">
          <p className="text-[15px] font-medium">“{made.title}” is ready</p>
          <p className="mt-1 text-sm text-ink-2">
            {made.vocabulary_count} words, {made.grammar_count} grammar notes, {made.flashcard_count} cards.
          </p>
          <Button className="mt-3" size="sm" variant="secondary" onClick={() => nav.open({ kind: 'unit', id: made.unit_id })}>
            Open lesson
          </Button>
        </Panel>
      )}

      <form onSubmit={submit} className="mt-6 space-y-5">
        <Field label="Title">
          <input className={inputCls} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="At the bakery" required />
        </Field>
        <Field label="Level">
          <select className={inputCls} value={level} onChange={(e) => setLevel(e.target.value)}>
            {LEVELS.map((l) => <option key={l} value={l}>{l}</option>)}
          </select>
        </Field>
        <Field label="Text">
          <textarea
            className={`${inputCls} min-h-48 leading-relaxed`}
            value={text}
            onChange={(e) => setText(e.target.value)}
            lang={pair.target}
            dir={dirOf(pair.target)}
            required
          />
        </Field>

        <ErrorNote error={error} />

        <div className="flex flex-wrap items-center gap-4">
          <Button type="submit" disabled={busy || !text.trim() || !title.trim() || pair.source === pair.target}>
            Make a lesson
          </Button>
          {busy && <Spinner label={`Working · ${formatElapsed(elapsed)}`} />}
        </div>
        <p className="text-[13px] text-ink-3">
          With a local model this can take several minutes. You can leave this page; the lesson appears under Your lessons when it’s done.
        </p>
      </form>
    </div>
  )
}
