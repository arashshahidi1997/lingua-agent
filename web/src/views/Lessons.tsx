import { useEffect, useState } from 'react'
import { api, type UnitDetail, type UnitListItem } from '../lib/api'
import { isRtl } from '../lib/rtl'
import { Button, Card, ErrorBanner, Loading, Section } from '../components/ui'

export default function Lessons() {
  const [units, setUnits] = useState<UnitListItem[] | null>(null)
  const [open, setOpen] = useState<UnitDetail | null>(null)
  const [openLoading, setOpenLoading] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [reload, setReload] = useState(0)

  useEffect(() => {
    api.units().then(setUnits).catch((e) => setError(String(e)))
  }, [reload])

  const showUnit = async (id: string) => {
    setError(null); setOpenLoading(id)
    try {
      const detail = await api.unitDetail(id)
      setOpen(detail)
    } catch (e) {
      setError(String(e))
    } finally {
      setOpenLoading(null)
    }
  }

  return (
    <Section
      title="Lesson units"
      action={
        <Button variant="secondary" size="sm" onClick={() => setReload((n) => n + 1)}>
          Refresh
        </Button>
      }
    >
      <ErrorBanner error={error} />
      {!units && !error && <Loading />}
      {units && units.length === 0 && (
        <p className="text-slate-500">
          No lessons yet. Use the <strong>Ingest</strong> tab to create one.
        </p>
      )}
      {units && units.length > 0 && (
        <ul className="grid gap-3 sm:grid-cols-2">
          {units.map((u) => (
            <li key={u.id}>
              <button
                onClick={() => showUnit(u.id)}
                disabled={openLoading === u.id}
                className="block w-full rounded-lg border border-slate-200 bg-white p-4 text-left transition hover:border-violet-300 hover:shadow disabled:opacity-50"
              >
                <div className="text-xs uppercase tracking-wide text-slate-500">
                  {u.source_language} → {u.target_language} · {u.cefr_level ?? '—'}
                </div>
                <div className="mt-1 font-medium">{u.title}</div>
                <div className="mt-2 text-xs text-slate-500">
                  {u.vocabulary_count} vocab · {u.flashcard_count} cards · {u.exercise_count} exercises
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}

      {open && <UnitModal unit={open} onClose={() => setOpen(null)} />}
    </Section>
  )
}

function UnitModal({ unit, onClose }: { unit: UnitDetail; onClose: () => void }) {
  const targetRtl = isRtl(unit.target_language)
  const target = unit.target_language

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"
      onClick={onClose}
    >
      <div
        className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-lg bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4">
          <div>
            <h3 className="text-lg font-semibold">{unit.title}</h3>
            <p className="text-xs text-slate-500">
              {unit.source_language} → {unit.target_language} · {unit.cefr_level ?? '—'}
              {unit.tags.length > 0 && (
                <> · {unit.tags.map((t) => `#${t}`).join(' ')}</>
              )}
            </p>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>Close ✕</Button>
        </div>

        <div className="space-y-6 px-6 py-5">
          {unit.summary && (
            <Card title="Summary">
              <p className="text-sm" dir={targetRtl ? 'rtl' : 'ltr'}>{unit.summary}</p>
            </Card>
          )}

          {unit.bilingual_reading.length > 0 && (
            <Card title="Bilingual reading">
              <table className="w-full table-fixed text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                    <th className="w-1/2 pb-2 pr-3">{unit.source_language}</th>
                    <th className="w-1/2 pb-2 pl-3">{unit.target_language}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 align-top">
                  {unit.bilingual_reading.map((p, i) => (
                    <tr key={i}>
                      <td className="py-2 pr-3">{p.source}</td>
                      <td className="py-2 pl-3" dir={targetRtl ? 'rtl' : 'ltr'}>{p.target}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          )}

          {unit.vocabulary.length > 0 && (
            <Card title={`Vocabulary (${unit.vocabulary.length})`}>
              <ul className="divide-y divide-slate-100">
                {unit.vocabulary.map((v) => {
                  const translations = v.translations[target] ?? []
                  return (
                    <li key={v.id} className="py-2">
                      <div className="flex flex-wrap items-baseline gap-2">
                        <span className="font-medium" dir={targetRtl ? 'rtl' : 'ltr'}>{v.lemma}</span>
                        {v.pos && <span className="text-xs text-slate-500">_{v.pos}_</span>}
                        {v.gender && <span className="text-xs italic text-slate-500">{v.gender}.</span>}
                        {v.cefr_level && (
                          <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium uppercase text-slate-600">
                            {v.cefr_level}
                          </span>
                        )}
                      </div>
                      <div className="mt-0.5 text-sm text-slate-700">
                        → {translations.join(', ') || <span className="text-slate-400">—</span>}
                      </div>
                      {v.transliteration && (
                        <div className="text-xs text-slate-500">/{v.transliteration}/</div>
                      )}
                      {v.example_text && (
                        <div className="mt-1 text-xs italic text-slate-500">"{v.example_text}"</div>
                      )}
                    </li>
                  )
                })}
              </ul>
            </Card>
          )}

          {unit.grammar.length > 0 && (
            <Card title={`Grammar (${unit.grammar.length})`}>
              <ul className="space-y-3">
                {unit.grammar.map((g) => (
                  <li key={g.id}>
                    <div className="font-medium">{g.name}</div>
                    <p className="mt-0.5 text-sm text-slate-700">{g.summary}</p>
                    {g.evidence.length > 0 && (
                      <ul className="mt-1 list-inside list-disc text-xs text-slate-500">
                        {g.evidence.map((ev, i) => (
                          <li key={i}>{ev}</li>
                        ))}
                      </ul>
                    )}
                  </li>
                ))}
              </ul>
            </Card>
          )}

          {unit.exercises.length > 0 && (
            <Card title={`Exercises (${unit.exercises.length})`}>
              <ol className="space-y-3">
                {unit.exercises.map((e, i) => (
                  <li key={e.id} className="text-sm">
                    <div className="flex items-baseline gap-2">
                      <span className="text-slate-400">{i + 1}.</span>
                      <span className="rounded bg-violet-100 px-1.5 py-0.5 text-[10px] font-medium uppercase text-violet-900">
                        {e.type}
                      </span>
                      <span className="text-xs text-slate-400">difficulty {e.difficulty}</span>
                    </div>
                    <p className="mt-1" dir={targetRtl ? 'rtl' : 'ltr'}>{e.prompt}</p>
                    {e.expected_answer && (
                      <p className="mt-0.5 text-xs text-slate-500">
                        expected: <span dir={targetRtl ? 'rtl' : 'ltr'}>{e.expected_answer}</span>
                      </p>
                    )}
                    {e.choices.length > 0 && (
                      <p className="mt-0.5 text-xs text-slate-500">choices: {e.choices.join(', ')}</p>
                    )}
                    {e.explanation && (
                      <p className="mt-0.5 text-xs italic text-slate-500">{e.explanation}</p>
                    )}
                  </li>
                ))}
              </ol>
            </Card>
          )}

          {unit.flashcards.length > 0 && (
            <Card title={`Flashcards (${unit.flashcards.length})`}>
              <table className="w-full text-sm">
                <thead className="text-left text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="pb-2 pr-3">Front</th>
                    <th className="pb-2 pl-3">Back</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {unit.flashcards.map((c) => (
                    <tr key={c.id}>
                      <td className="py-1.5 pr-3" dir={isRtl(c.source_language) ? 'rtl' : 'ltr'}>
                        {c.front}
                      </td>
                      <td className="py-1.5 pl-3" dir={isRtl(c.target_language) ? 'rtl' : 'ltr'}>
                        {c.back}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
