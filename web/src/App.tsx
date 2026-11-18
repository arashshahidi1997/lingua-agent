import { useCallback, useEffect, useRef, useSyncExternalStore, type ReactNode } from 'react'
import { BookOpen, CloudOff, Library as LibraryIcon, MessageCircle, Route, Settings as SettingsIcon } from 'lucide-react'
import { onSynced, pendingCount, startOfflineSync, subscribeQueue } from './lib/offline'
import { CarpetMargins } from './components/Carpet'
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
import ChatbotPrompt from './views/ChatbotPrompt'
import ClozeReader from './views/ClozeReader'
import GrammarTopicView from './views/GrammarTopic'
import VoiceReview from './views/VoiceReview'
import { useTalkEnabled } from './lib/features'

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
  const { tab, setTab, stack, open, bumpData } = useNav()
  const mainRef = useRef<HTMLElement>(null)
  const pending = useSyncExternalStore(subscribeQueue, pendingCount)

  // Progress saved offline goes up when the connection is back; refetch once it has.
  useEffect(() => {
    startOfflineSync()
    return onSynced(bumpData)
  }, [bumpData])

  // After switching tabs, focus moves to the page (not left on the tab button), so screen readers land on
  // the new content and a key press doesn't light up the rail.
  const go = useCallback((t: Tab) => {
    setTab(t)
    mainRef.current?.focus({ preventScroll: true })
  }, [setTab])

  return (
    <div className="min-h-dvh bg-canvas text-ink">
      <CarpetMargins />
      {/* Rail on ≥ md */}
      <nav aria-label="Main" className="fixed inset-y-0 start-0 z-30 hidden w-20 flex-col items-center gap-1 border-e border-line bg-canvas pt-6 md:flex">
        <div className="mb-6 text-[13px] font-semibold tracking-tight text-accent" aria-hidden>lingua</div>
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => go(t.key)}
            aria-current={tab === t.key ? 'page' : undefined}
            className={`flex w-16 flex-col items-center gap-1 rounded-2xl py-2.5 text-[11px] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-accent ${
              tab === t.key ? 'bg-accent-soft font-medium text-accent' : 'text-ink-3 hover:bg-hover hover:text-ink'
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
              {pending > 0 && (
                <span role="status" title="Saved offline — will sync" className="inline-flex items-center gap-1.5 text-[12px] text-ink-3">
                  <CloudOff size={16} aria-hidden />
                  <span className="hidden sm:inline">Saved offline — will sync</span>
                  <span className="sr-only sm:hidden">Saved offline — will sync</span>
                </span>
              )}
              <PairChip />
              <IconButton label="Settings" onClick={() => open({ kind: 'settings' })}>
                <SettingsIcon size={20} strokeWidth={1.75} />
              </IconButton>
            </div>
          </div>
        </header>

        <main ref={mainRef} tabIndex={-1} aria-label={TABS.find((t) => t.key === tab)?.label} className="relative pb-28 pt-4 outline-none md:pb-16">
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
              onClick={() => go(t.key)}
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
  const talkOn = useTalkEnabled()
  switch (overlay.kind) {
    case 'settings': return <Settings />
    case 'lesson-sheet': return <LessonSheet courseId={overlay.courseId} lessonId={overlay.lessonId} locked={overlay.locked} />
    case 'player': return <Player source={overlay.source} />
    case 'review': return <Review />
    case 'story': return <StoryReader id={overlay.id} />
    case 'cloze': return <ClozeReader storyId={overlay.storyId} />
    case 'voice-review': return <VoiceReview />
    case 'grammar': return <GrammarTopicView courseId={overlay.courseId} topicId={overlay.topicId} />
    case 'audio': return <AudioPlayer id={overlay.id} />
    case 'unit': return <UnitReader id={overlay.id} />
    case 'talk':
      // Built-in Talk is off until a good enough model is set: role-plays open as prompts for your own chatbot.
      if (talkOn === null) return null
      if (!talkOn) return overlay.scenarioId ? <ChatbotPrompt scenarioId={overlay.scenarioId} /> : null
      return <TalkChat scenarioId={overlay.scenarioId} />
  }
}
