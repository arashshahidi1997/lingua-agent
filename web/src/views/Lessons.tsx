import { useEffect, useState } from 'react'
import { api, type LessonUnit, type UnitListItem } from '../lib/api'
import { isRtl } from '../lib/rtl'
import { Button, Card, ErrorBanner, Loading, Section } from '../components/ui'

export default function Lessons() {
  const [units, setUnits] = useState<UnitListItem[] | null>(null)
  const [open, setOpen] = useState<LessonUnit | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [reload, setReload] = useState(0)

  useEffect(() => {
    api.units().then(setUnits).catch((e) => setError(String(e)))
  }, [reload])

  const showUnit = async (id: string) => {
    setError(null)
    try {
      const unit = await api.unit(id)
      setOpen(unit)
    } catch (e) {
      setError(String(e))
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
                className="block w-full rounded-lg border border-slate-200 bg-white p-4 text-left transition hover:border-violet-300 hover:shadow"
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

function UnitModal({ unit, onClose }: { unit: LessonUnit; onClose: () => void }) {
  const targetRtl = isRtl(unit.target_language)
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

          <Card title="Counts">
            <ul className="text-sm text-slate-700">
              <li>Vocabulary: {unit.vocabulary_ids.length}</li>
              <li>Grammar points: {unit.grammar_ids.length}</li>
              <li>Exercises: {unit.exercise_ids.length}</li>
              <li>Flashcards: {unit.flashcard_ids.length}</li>
            </ul>
            <p className="mt-3 text-xs text-slate-500">
              Detailed vocab / grammar / exercise rendering will land in a follow-up; the
              underlying data is already in the unit JSON and on disk.
            </p>
          </Card>
        </div>
      </div>
    </div>
  )
}
