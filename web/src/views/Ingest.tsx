import { useState } from 'react'
import { api, type IngestSummary } from '../lib/api'
import { useLangPair } from '../state/LangPair'
import { Button, Card, ErrorBanner, Section } from '../components/ui'

const LEVELS = [null, 'A1', 'A2', 'B1', 'B2', 'C1', 'C2'] as const

export default function Ingest({ onCreated }: { onCreated?: (s: IngestSummary) => void }) {
  const { pair } = useLangPair()
  const [title, setTitle] = useState('Coffee conversation')
  const [text, setText] = useState(
    'I would like a coffee and a glass of water. Where is the train station?',
  )
  const [level, setLevel] = useState<string | null>('A1')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [last, setLast] = useState<IngestSummary | null>(null)

  const submit = async () => {
    setBusy(true)
    setError(null)
    try {
      const summary = await api.ingestText({
        text, title,
        source_language: pair.source,
        target_language: pair.target,
        support_language: pair.support,
        cefr_level: level,
      })
      setLast(summary)
      onCreated?.(summary)
    } catch (e) {
      setError(String(e))
    } finally {
      setBusy(false)
    }
  }

  const disabled = busy || !text.trim() || !title.trim() || pair.source === pair.target

  return (
    <Section title="Ingest custom material">
      <ErrorBanner error={error} />
      <Card>
        <div className="space-y-3">
          <label className="block text-sm">
            <span className="text-slate-500">Title</span>
            <input
              className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </label>
          <label className="block text-sm">
            <span className="text-slate-500">CEFR level</span>
            <select
              className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              value={level ?? ''}
              onChange={(e) => setLevel(e.target.value || null)}
            >
              {LEVELS.map((lv) => (
                <option key={lv ?? ''} value={lv ?? ''}>{lv ?? '— unspecified —'}</option>
              ))}
            </select>
          </label>
          <label className="block text-sm">
            <span className="text-slate-500">Material</span>
            <textarea
              className="mt-1 block h-40 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
          </label>
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500">
              Pair: <span className="font-mono">{pair.source} → {pair.target}</span>
              {pair.support && <> · support <span className="font-mono">{pair.support}</span></>}
            </span>
            <Button onClick={submit} disabled={disabled}>
              {busy ? 'Generating…' : 'Ingest'}
            </Button>
          </div>
        </div>
      </Card>
      {last && (
        <Card title="Just created">
          <p className="text-sm">
            <span className="font-mono text-violet-700">{last.unit_id}</span>
            {' — '}
            {last.vocabulary_count} vocab, {last.grammar_count} grammar, {last.exercise_count} exercises,{' '}
            {last.flashcard_count} cards.
          </p>
          {last.unit_path && <p className="mt-1 text-xs text-slate-500">Markdown: <code>{last.unit_path}</code></p>}
        </Card>
      )}
    </Section>
  )
}
