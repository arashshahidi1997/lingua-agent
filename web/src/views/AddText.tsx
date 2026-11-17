import { useState, type FormEvent } from 'react'
import { ArrowLeft } from 'lucide-react'
import { formatElapsed, useSecondsSince } from '../lib/hooks'
import { clearIngest, startIngest, useIngestJob } from '../lib/pending-ingest'
import { dirOf, languageName } from '../lib/rtl'
import { useNav } from '../state/nav'
import { useSettings } from '../state/settings'
import { Button, ErrorNote, Field, Panel, Segmented, Spinner, inputCls } from '../components/ui'

const LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']

/** "+ Add": paste a text and turn it into a lesson. The text can be in the language being learned or in your own. */
export default function AddText({ onBack }: { onBack: () => void }) {
  const { pair } = useSettings()
  const nav = useNav()
  const job = useIngestJob()
  const [title, setTitle] = useState('')
  const [text, setText] = useState('')
  const [level, setLevel] = useState('A1')
  // Which language the pasted text is written in (D2: chosen per text).
  const [textLang, setTextLang] = useState<'target' | 'source'>('target')
  const busy = !!job && !job.done
  const elapsed = useSecondsSince(busy && job ? job.startedAt : null)
  const writtenIn = textLang === 'target' ? pair.target : pair.source

  const submit = (e: FormEvent) => {
    e.preventDefault()
    startIngest({
      text: text.trim(),
      title: title.trim(),
      source_language: writtenIn,
      target_language: pair.target,
      support_language: pair.support,
      cefr_level: level,
    }, nav.bumpData)
    setText(''); setTitle('')
  }

  return (
    <div>
      <button type="button" onClick={onBack} className="mb-4 inline-flex items-center gap-1.5 rounded-lg text-sm text-ink-2 hover:text-ink">
        <ArrowLeft size={16} className="rtl:rotate-180" aria-hidden /> Library
      </button>
      <h2 className="text-xl font-semibold tracking-tight">Add your own text</h2>
      <p className="mt-1 text-[15px] text-ink-2">
        Paste a {languageName(pair.target)} text (an article, a song you own, a dialogue from a course book), or
        a {languageName(pair.source)} one to learn how to say it in {languageName(pair.target)}.
        It becomes a lesson with vocabulary, grammar notes and flashcards.
      </p>

      {busy && job && (
        <Panel className="mt-6 flex items-center justify-between gap-3 p-4">
          <p className="min-w-0 text-[15px]">“{job.title}” is still being made</p>
          <Spinner label={formatElapsed(elapsed)} />
        </Panel>
      )}

      {job?.done && job.result && (
        <Panel className="mt-6 p-4">
          <p className="text-[15px] font-medium">“{job.result.title}” is ready</p>
          <p className="mt-1 text-sm text-ink-2">
            {job.result.vocabulary_count} words, {job.result.grammar_count} grammar notes, {job.result.flashcard_count} cards.
          </p>
          <div className="mt-3 flex gap-2">
            <Button size="sm" variant="secondary" onClick={() => nav.open({ kind: 'unit', id: job.result!.unit_id })}>
              Open lesson
            </Button>
            <Button size="sm" variant="ghost" onClick={clearIngest}>Dismiss</Button>
          </div>
        </Panel>
      )}
      {job?.done && job.error && (
        <div className="mt-6"><ErrorNote error={`“${job.title}” couldn’t be made. ${job.error}`} /></div>
      )}

      <form onSubmit={submit} className="mt-6 space-y-5">
        <Field label="Title">
          <input className={inputCls} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="At the bakery" required />
        </Field>
        <div>
          <p className="mb-1.5 text-sm font-medium text-ink-2">The text is in</p>
          <Segmented
            label="The text is in"
            value={textLang}
            onChange={setTextLang}
            options={[
              { value: 'target', label: languageName(pair.target) },
              { value: 'source', label: languageName(pair.source) },
            ]}
          />
        </div>
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
            lang={writtenIn}
            dir={dirOf(writtenIn)}
            required
          />
        </Field>

        <div className="flex flex-wrap items-center gap-4">
          <Button type="submit" disabled={busy || !text.trim() || !title.trim() || pair.source === pair.target}>
            Make a lesson
          </Button>
          {busy && <span className="text-[13px] text-ink-3">One at a time: wait for the current one to finish.</span>}
        </div>
        <p className="text-[13px] text-ink-3">
          With a local model this can take several minutes. You can leave this page; the lesson appears under Your lessons when it’s done.
        </p>
      </form>
    </div>
  )
}
