import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { NavContext, type LibrarySection, type Overlay, type Tab } from './nav'
import { loadJson, saveJson } from './settings'

const K_TAB = 'lingua.tab'
const K_LIB = 'lingua.librarySection'

const depthOf = (state: unknown): number =>
  state && typeof state === 'object' && 'depth' in state && typeof state.depth === 'number' ? state.depth : 0

export function NavProvider({ children }: { children: ReactNode }) {
  const [tab, setTabState] = useState<Tab>(() => loadJson<Tab>(K_TAB, 'today'))
  const [librarySection, setLib] = useState<LibrarySection>(() => loadJson<LibrarySection>(K_LIB, 'stories'))
  const [stack, setStack] = useState<Overlay[]>([])
  const [dataVersion, setDataVersion] = useState(0)

  useEffect(() => {
    // A reload while an overlay was open leaves a deep history entry behind; start clean.
    if (depthOf(window.history.state) !== 0) window.history.replaceState({ depth: 0 }, '')
    const onPop = (e: PopStateEvent) => {
      const depth = depthOf(e.state)
      setStack((s) => (s.length > depth ? s.slice(0, depth) : s))
    }
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  const open = useCallback((o: Overlay) => {
    window.history.pushState({ depth: depthOf(window.history.state) + 1 }, '')
    setStack((s) => [...s, o])
  }, [])

  const replace = useCallback((o: Overlay) => {
    setStack((s) => (s.length ? [...s.slice(0, -1), o] : [o]))
  }, [])

  const close = useCallback(() => {
    if (depthOf(window.history.state) > 0) window.history.back()
    else setStack((s) => s.slice(0, -1))
  }, [])

  const setTab = useCallback((t: Tab) => {
    setTabState(t)
    saveJson(K_TAB, t)
    window.scrollTo({ top: 0 })
  }, [])

  const setLibrarySection = useCallback((s: LibrarySection) => {
    setLib(s)
    saveJson(K_LIB, s)
  }, [])

  const bumpData = useCallback(() => setDataVersion((v) => v + 1), [])

  const value = useMemo(() => ({
    tab, setTab, librarySection, setLibrarySection, stack, open, replace, close, dataVersion, bumpData,
  }), [tab, setTab, librarySection, setLibrarySection, stack, open, replace, close, dataVersion, bumpData])

  return <NavContext value={value}>{children}</NavContext>
}
