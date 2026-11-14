import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { configureSpeech } from '../lib/speech'
import {
  DEFAULT_PAIR, DEFAULT_SETTINGS, SettingsContext, loadJson, samePair, saveJson,
  type Pair, type Settings,
} from './settings'

const K_SETTINGS = 'lingua.settings'
const K_PAIR = 'lingua.pair'
const K_RECENT = 'lingua.recentPairs'

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<Settings>(() => {
    const loaded = loadJson(K_SETTINGS, DEFAULT_SETTINGS)
    configureSpeech({ mode: loaded.voice, rate: loaded.rate })
    return loaded
  })
  const [pair, setPairState] = useState<Pair>(() => loadJson(K_PAIR, DEFAULT_PAIR))
  const [recentPairs, setRecent] = useState<Pair[]>(() => {
    const r = loadJson<Pair[]>(K_RECENT, [])
    return Array.isArray(r) ? r : []
  })

  useEffect(() => { saveJson(K_SETTINGS, settings) }, [settings])
  useEffect(() => { saveJson(K_PAIR, pair) }, [pair])
  useEffect(() => { saveJson(K_RECENT, recentPairs) }, [recentPairs])

  const value = useMemo(() => ({
    settings,
    update: (patch: Partial<Settings>) => {
      const next = { ...settings, ...patch }
      // The speech module lives outside React; keep it in step right away.
      configureSpeech({ mode: next.voice, rate: next.rate })
      setSettings(next)
    },
    pair,
    setPair: (p: Pair) => {
      if (samePair(pair, p)) return
      setRecent((r) => [pair, ...r.filter((x) => !samePair(x, pair) && !samePair(x, p))].slice(0, 4))
      setPairState(p)
    },
    recentPairs,
  }), [settings, pair, recentPairs])

  return <SettingsContext value={value}>{children}</SettingsContext>
}
