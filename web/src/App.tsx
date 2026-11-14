import type { ReactNode } from 'react'
import { BookOpen, Library as LibraryIcon, MessageCircle, Route, Settings as SettingsIcon } from 'lucide-react'
import { SettingsProvider } from './state/SettingsProvider'
import { NavProvider } from './state/NavProvider'
import { useNav, type Overlay, type Tab } from './state/nav'
import { PairChip } from './components/PairChip'
import { Hints } from './components/Hints'
import { IconButton } from './components/ui'
import Today from './views/Today'
import PathView from './views/Path'
import Library from './views/Library'
import Talk from './views/Talk'
import Settings from './views/Settings'
import Player from './views/Player'
import Review from './views/Review'
import LessonSheet from './views/LessonSheet'
import StoryReader from './views/StoryReader'
import AudioPlayer from './views/AudioPlayer'
import UnitReader from './views/UnitReader'
import TalkChat from './views/TalkChat'

const TABS: { key: Tab; label: string; icon: ReactNode }[] = [
  { key: 'today', label: 'Today', icon: <BookOpen size={22} strokeWidth={1.75} /> },
  { key: 'path', label: 'Path', icon: <Route size={22} strokeWidth={1.75} /> },
  { key: 'library', label: 'Library', icon: <LibraryIcon size={22} strokeWidth={1.75} /> },
  { key: 'talk', label: 'Talk', icon: <MessageCircle size={22} strokeWidth={1.75} /> },
]

export default function App() {
  return (
    <SettingsProvider>
      <NavProvider>
        <Shell />
      </NavProvider>
    </SettingsProvider>
  )
}

function Shell() {
  const { tab, setTab, stack, open } = useNav()

  return (
    <div className="min-h-dvh bg-canvas text-ink">
      {/* Rail on ≥ md */}
      <nav aria-label="Main" className="fixed inset-y-0 start-0 z-30 hidden w-20 flex-col items-center gap-1 border-e border-line bg-canvas pt-6 md:flex">
        <div className="mb-6 text-[13px] font-semibold tracking-tight text-accent" aria-hidden>lingua</div>
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTab(t.key)}
            aria-current={tab === t.key ? 'page' : undefined}
            className={`flex w-16 flex-col items-center gap-1 rounded-2xl py-2.5 text-[11px] transition-colors ${
              tab === t.key ? 'bg-accent-soft font-medium text-accent' : 'text-ink-3 hover:bg-surface-2 hover:text-ink'
            }`}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </nav>

      <div className="md:ps-20">
        <header className="pt-safe sticky top-0 z-20 border-b border-line/60 bg-canvas/92 backdrop-blur-sm">
          <div className="mx-auto flex h-14 max-w-3xl items-center justify-between gap-3 px-4 sm:px-6">
            <span className="text-[15px] font-semibold tracking-tight text-ink md:invisible">lingua</span>
            <div className="flex items-center gap-1.5">
              <PairChip />
              <IconButton label="Settings" onClick={() => open({ kind: 'settings' })}>
                <SettingsIcon size={20} strokeWidth={1.75} />
              </IconButton>
            </div>
          </div>
        </header>

        <main className="pb-28 pt-4 md:pb-16">
          {tab === 'today' && <Today />}
          {tab === 'path' && <PathView />}
          {tab === 'library' && <Library />}
          {tab === 'talk' && <Talk />}
        </main>
      </div>

      {/* Bottom tab bar on phones */}
      <nav aria-label="Main" className="pb-safe fixed inset-x-0 bottom-0 z-30 border-t border-line bg-canvas/95 backdrop-blur-sm md:hidden">
        <div className="mx-auto grid max-w-md grid-cols-4">
          {TABS.map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => setTab(t.key)}
              aria-current={tab === t.key ? 'page' : undefined}
              className={`flex flex-col items-center gap-0.5 pb-2 pt-2.5 text-[11px] transition-colors ${
                tab === t.key ? 'font-medium text-accent' : 'text-ink-3'
              }`}
            >
              {t.icon}
              {t.label}
            </button>
          ))}
        </div>
      </nav>

      {stack.map((o, i) => <OverlayView key={`${i}-${o.kind}`} overlay={o} />)}
      <Hints />
    </div>
  )
}

function OverlayView({ overlay }: { overlay: Overlay }) {
  switch (overlay.kind) {
    case 'settings': return <Settings />
    case 'lesson-sheet': return <LessonSheet courseId={overlay.courseId} lessonId={overlay.lessonId} locked={overlay.locked} />
    case 'player': return <Player source={overlay.source} />
    case 'review': return <Review />
    case 'story': return <StoryReader id={overlay.id} />
    case 'audio': return <AudioPlayer id={overlay.id} />
    case 'unit': return <UnitReader id={overlay.id} />
    case 'talk': return <TalkChat scenarioId={overlay.scenarioId} />
  }
}
