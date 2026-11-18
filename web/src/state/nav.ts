import { createContext, useContext } from 'react'

export type Tab = 'today' | 'path' | 'library' | 'talk'
export type LibrarySection = 'stories' | 'audio' | 'lessons' | 'add'

export type PlayerSource =
  | { type: 'lesson'; courseId: string; lessonId: string; title?: string; fast?: boolean }
  | { type: 'quiz'; courseId: string; unitId: string; title?: string; testOut?: boolean }
  | { type: 'practice'; courseId: string }

/** Screens stacked over the tabs. Each one gets a history entry, so the Android back button closes it. */
export type Overlay =
  | { kind: 'settings' }
  | { kind: 'lesson-sheet'; courseId: string; lessonId: string; locked: boolean }
  | { kind: 'player'; source: PlayerSource }
  | { kind: 'review' }
  | { kind: 'story'; id: string }
  | { kind: 'cloze'; storyId: string }
  | { kind: 'audio'; id: string }
  | { kind: 'unit'; id: string }
  | { kind: 'talk'; scenarioId: string | null }

export interface NavCtx {
  tab: Tab
  setTab: (t: Tab) => void
  librarySection: LibrarySection
  setLibrarySection: (s: LibrarySection) => void
  stack: Overlay[]
  open: (o: Overlay) => void
  /** Swap the top overlay for another (no new history entry). */
  replace: (o: Overlay) => void
  close: () => void
  /** Bumped after anything that changes progress, so Today and Path refetch. */
  dataVersion: number
  bumpData: () => void
}

export const NavContext = createContext<NavCtx | null>(null)

export function useNav(): NavCtx {
  const ctx = useContext(NavContext)
  if (!ctx) throw new Error('useNav must be used inside <NavProvider>')
  return ctx
}

export const isSheet = (o: Overlay) => o.kind === 'lesson-sheet'
