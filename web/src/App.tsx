import { useEffect, useState, type ReactNode } from 'react'
import { api, type Health, type Language, type UnitListItem, type Card } from './lib/api'

type ViewKey = 'dashboard' | 'languages' | 'units' | 'review'

const NAV: { key: ViewKey; label: string; icon: string }[] = [
  { key: 'dashboard', label: 'Dashboard', icon: '🏠' },
  { key: 'languages', label: 'Languages', icon: '🌐' },
  { key: 'units', label: 'Lessons', icon: '📖' },
  { key: 'review', label: 'Review', icon: '🃏' },
]

export default function App() {
  const [view, setView] = useState<ViewKey>('dashboard')

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto flex max-w-7xl">
        <aside className="hidden w-56 shrink-0 border-r border-slate-200 bg-white p-4 sm:block">
          <h1 className="mb-1 text-lg font-bold tracking-tight">📚 lingua-agent</h1>
          <p className="mb-6 text-xs text-slate-500">any A → any B</p>
          <nav className="space-y-1">
            {NAV.map((item) => (
              <button
                key={item.key}
                onClick={() => setView(item.key)}
                className={`flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm transition ${
                  view === item.key
                    ? 'bg-violet-100 text-violet-900'
                    : 'text-slate-700 hover:bg-slate-100'
                }`}
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </button>
            ))}
          </nav>
        </aside>

        <main className="flex-1 p-6">
          {view === 'dashboard' && <DashboardView />}
          {view === 'languages' && <LanguagesView />}
          {view === 'units' && <UnitsView />}
          {view === 'review' && <ReviewView />}
        </main>
      </div>
    </div>
  )
}

// ---- Dashboard --------------------------------------------------------------

function DashboardView() {
  const [health, setHealth] = useState<Health | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.health().then(setHealth).catch((e) => setError(String(e)))
  }, [])

  return (
    <Section title="Dashboard">
      <Card title="Backend">
        {error && <p className="text-rose-700">⚠ {error}</p>}
        {!health && !error && <p className="text-slate-500">Pinging backend…</p>}
        {health && (
          <ul className="space-y-1 text-sm">
            <li><span className="text-slate-500">status:</span> <span className="font-medium">{health.status}</span></li>
            <li><span className="text-slate-500">version:</span> <span className="font-medium">{health.version}</span></li>
            <li><span className="text-slate-500">AI provider:</span> <span className="font-medium">{health.ai_provider}</span></li>
          </ul>
        )}
      </Card>
      <Card title="Up next">
        <p className="text-sm text-slate-600">
          Phase 8.2 will add Ingest, full Lessons view, and Tutor chat tabs, plus PWA manifest +
          service worker so this installs to your phone's home screen.
        </p>
      </Card>
    </Section>
  )
}

// ---- Languages --------------------------------------------------------------

function LanguagesView() {
  const [langs, setLangs] = useState<Language[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.languages().then(setLangs).catch((e) => setError(String(e)))
  }, [])

  return (
    <Section title="Supported languages">
      {error && <p className="text-rose-700">⚠ {error}</p>}
      {!langs && !error && <p className="text-slate-500">Loading…</p>}
      {langs && (
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-2">Code</th>
                <th className="px-4 py-2">Name</th>
                <th className="px-4 py-2">Native</th>
                <th className="px-4 py-2">Script</th>
                <th className="px-4 py-2">Direction</th>
                <th className="px-4 py-2">Transliteration</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {langs.map((lang) => (
                <tr key={lang.code}>
                  <td className="px-4 py-2 font-mono">{lang.code}</td>
                  <td className="px-4 py-2">{lang.name}</td>
                  <td className="px-4 py-2" dir={lang.direction}>{lang.native_name}</td>
                  <td className="px-4 py-2">{lang.script}</td>
                  <td className="px-4 py-2">{lang.direction}</td>
                  <td className="px-4 py-2">{lang.transliteration_supported ? 'yes' : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Section>
  )
}

// ---- Units ------------------------------------------------------------------

function UnitsView() {
  const [units, setUnits] = useState<UnitListItem[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.units().then(setUnits).catch((e) => setError(String(e)))
  }, [])

  return (
    <Section title="Lesson units">
      {error && <p className="text-rose-700">⚠ {error}</p>}
      {!units && !error && <p className="text-slate-500">Loading…</p>}
      {units && units.length === 0 && (
        <p className="text-slate-500">
          No lessons yet. Use the CLI for now: <code className="rounded bg-slate-100 px-1">lingua-agent ingest text …</code>.
          Phase 8.2 will add the Ingest form here.
        </p>
      )}
      {units && units.length > 0 && (
        <ul className="grid gap-3 sm:grid-cols-2">
          {units.map((u) => (
            <li key={u.id} className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="text-xs uppercase tracking-wide text-slate-500">
                {u.source_language} → {u.target_language} · {u.cefr_level ?? '—'}
              </div>
              <div className="mt-1 font-medium">{u.title}</div>
              <div className="mt-2 text-xs text-slate-500">
                {u.vocabulary_count} vocab · {u.flashcard_count} cards · {u.exercise_count} exercises
              </div>
            </li>
          ))}
        </ul>
      )}
    </Section>
  )
}

// ---- Review (placeholder) ---------------------------------------------------

function ReviewView() {
  const [cards, setCards] = useState<Card[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.cardsDue().then(setCards).catch((e) => setError(String(e)))
  }, [])

  return (
    <Section title="Review queue">
      {error && <p className="text-rose-700">⚠ {error}</p>}
      {!cards && !error && <p className="text-slate-500">Loading…</p>}
      {cards && cards.length === 0 && <p className="text-emerald-700">No cards due. ✓</p>}
      {cards && cards.length > 0 && (
        <p className="text-slate-700">
          {cards.length} card{cards.length === 1 ? '' : 's'} due. The reveal/grade UI ships in Phase 8.2.
        </p>
      )}
    </Section>
  )
}

// ---- Tiny presentational helpers -------------------------------------------

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-4">
      <h2 className="text-2xl font-semibold tracking-tight">{title}</h2>
      <div className="grid gap-4">{children}</div>
    </section>
  )
}

function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="mb-2 text-sm font-medium uppercase tracking-wide text-slate-500">{title}</h3>
      {children}
    </div>
  )
}
