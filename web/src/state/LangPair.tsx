import { createContext, useContext, useState, type ReactNode } from 'react'

export interface LangPair {
  source: string
  target: string
  support: string | null
}

interface Ctx {
  pair: LangPair
  setPair: (next: LangPair) => void
}

const LangPairContext = createContext<Ctx | null>(null)

export function LangPairProvider({ children }: { children: ReactNode }) {
  const [pair, setPair] = useState<LangPair>({ source: 'en', target: 'it', support: 'en' })
  return <LangPairContext value={{ pair, setPair }}>{children}</LangPairContext>
}

export function useLangPair(): Ctx {
  const ctx = useContext(LangPairContext)
  if (!ctx) throw new Error('useLangPair must be used inside <LangPairProvider>')
  return ctx
}
