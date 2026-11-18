import { createContext, useContext } from 'react'
import type { VoiceMode } from '../lib/speech'

export interface Pair {
  source: string   // the learner's language
  target: string   // the language being learned
  support: string  // language for explanations and glosses
}

export type ScriptDisplay = 'both' | 'script' | 'tr'

export interface Settings {
  script: ScriptDisplay
  showGloss: boolean
  voice: VoiceMode
  rate: 0.75 | 1
  dailyGoal: 5 | 10 | 15 | 20
  showStreak: boolean
  fastTrack: boolean      // Path: every lesson open, lessons run as quizzes
}

export const DEFAULT_PAIR: Pair = { source: 'en', target: 'fa', support: 'en' }

export const DEFAULT_SETTINGS: Settings = {
  script: 'both',
  showGloss: false,
  voice: 'auto',
  rate: 1,
  dailyGoal: 10,
  showStreak: false,
  fastTrack: false,
}

export interface SettingsCtx {
  settings: Settings
  update: (patch: Partial<Settings>) => void
  pair: Pair
  setPair: (p: Pair) => void
  recentPairs: Pair[]
}

export const SettingsContext = createContext<SettingsCtx | null>(null)

export function useSettings(): SettingsCtx {
  const ctx = useContext(SettingsContext)
  if (!ctx) throw new Error('useSettings must be used inside <SettingsProvider>')
  return ctx
}

export const samePair = (a: Pair, b: Pair) =>
  a.source === b.source && a.target === b.target && a.support === b.support

// ---- localStorage, always wrapped: it can throw or be empty -------------------

export function loadJson<T>(key: string, fallback: T): T {
  try {
    const raw = window.localStorage.getItem(key)
    if (!raw) return fallback
    const parsed = JSON.parse(raw)
    if (fallback && typeof fallback === 'object' && !Array.isArray(fallback)) {
      return { ...fallback, ...parsed }
    }
    return parsed as T
  } catch {
    return fallback
  }
}

export function saveJson(key: string, value: unknown) {
  try {
    window.localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // storage unavailable (private mode, quota): settings just won't persist
  }
}
