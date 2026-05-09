import { useState } from 'react'
import { LangPairProvider } from './state/LangPair'
import PairPicker from './components/PairPicker'
import Dashboard from './views/Dashboard'
import Languages from './views/Languages'
import Ingest from './views/Ingest'
import Lessons from './views/Lessons'
import Review from './views/Review'
import Tutor from './views/Tutor'

type ViewKey = 'dashboard' | 'languages' | 'ingest' | 'lessons' | 'review' | 'tutor'

const NAV: { key: ViewKey; label: string; icon: string }[] = [
  { key: 'dashboard', label: 'Dashboard', icon: '🏠' },
  { key: 'ingest',    label: 'Ingest',    icon: '📥' },
  { key: 'lessons',   label: 'Lessons',   icon: '📖' },
  { key: 'review',    label: 'Review',    icon: '🃏' },
  { key: 'tutor',     label: 'Tutor',     icon: '🤖' },
  { key: 'languages', label: 'Languages', icon: '🌐' },
]

export default function App() {
  const [view, setView] = useState<ViewKey>('dashboard')

  return (
    <LangPairProvider>
      <div className="min-h-screen bg-slate-50 text-slate-900">
        <div className="mx-auto flex max-w-7xl">
          <aside className="hidden w-60 shrink-0 space-y-6 border-r border-slate-200 bg-white p-4 sm:block">
            <div>
              <h1 className="mb-1 text-lg font-bold tracking-tight">📚 lingua-agent</h1>
              <p className="text-xs text-slate-500">any A → any B</p>
            </div>
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
            <div className="border-t border-slate-200 pt-4">
              <p className="mb-2 text-xs uppercase tracking-wide text-slate-500">Active pair</p>
              <PairPicker />
            </div>
          </aside>

          {/* Mobile top bar */}
          <div className="sm:hidden fixed inset-x-0 top-0 z-40 flex items-center gap-2 overflow-x-auto bg-white p-2 shadow">
            {NAV.map((item) => (
              <button
                key={item.key}
                onClick={() => setView(item.key)}
                className={`flex shrink-0 items-center gap-1 rounded-md px-3 py-1.5 text-xs ${
                  view === item.key ? 'bg-violet-100 text-violet-900' : 'text-slate-700'
                }`}
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </button>
            ))}
          </div>

          <main className="flex-1 p-6 pt-16 sm:pt-6">
            {view === 'dashboard' && <Dashboard />}
            {view === 'ingest'    && <Ingest />}
            {view === 'lessons'   && <Lessons />}
            {view === 'review'    && <Review />}
            {view === 'tutor'     && <Tutor />}
            {view === 'languages' && <Languages />}
          </main>
        </div>
      </div>
    </LangPairProvider>
  )
}
