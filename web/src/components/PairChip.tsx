import { useCallback, useState } from 'react'
import { Check, Settings as SettingsIcon } from 'lucide-react'
import { useDismiss } from '../lib/hooks'
import { languageName, shortLabel } from '../lib/rtl'
import { samePair, useSettings, type Pair } from '../state/settings'
import { useNav } from '../state/nav'

function PairLabel({ pair }: { pair: Pair }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span>{shortLabel(pair.source)}</span>
      <span aria-hidden className="text-ink-3">→</span>
      <span lang={pair.target}>{shortLabel(pair.target)}</span>
    </span>
  )
}

export function PairChip() {
  const { pair, setPair, recentPairs } = useSettings()
  const { open } = useNav()
  const [menu, setMenu] = useState(false)
  const close = useCallback(() => setMenu(false), [])
  const ref = useDismiss(menu, close)
  const pairs = [pair, ...recentPairs.filter((p) => !samePair(p, pair))]

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={menu}
        aria-label={`Language pair: ${languageName(pair.source)} to ${languageName(pair.target)}`}
        onClick={() => setMenu((m) => !m)}
        className="h-9 rounded-full border border-line-strong bg-surface px-3.5 text-[13px] font-medium text-ink transition-colors hover:bg-surface-2"
      >
        <PairLabel pair={pair} />
      </button>
      {menu && (
        <div role="menu" className="anim-in absolute end-0 top-11 z-50 w-60 rounded-2xl border border-line bg-surface p-1.5 shadow-[0_8px_24px_-12px_rgba(0,0,0,0.25)]">
          {pairs.map((p) => {
            const active = samePair(p, pair)
            return (
              <button
                key={`${p.source}-${p.target}-${p.support}`}
                role="menuitemradio"
                aria-checked={active}
                type="button"
                onClick={() => { setPair(p); close() }}
                className="flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-start text-sm text-ink hover:bg-surface-2"
              >
                <span>
                  {languageName(p.source)} → {languageName(p.target)}
                </span>
                {active && <Check size={16} className="text-accent" aria-hidden />}
              </button>
            )
          })}
          <div className="my-1 border-t border-line" />
          <button
            role="menuitem"
            type="button"
            onClick={() => { close(); open({ kind: 'settings' }) }}
            className="flex w-full items-center gap-2 rounded-xl px-3 py-2.5 text-start text-sm text-ink-2 hover:bg-surface-2"
          >
            <SettingsIcon size={16} aria-hidden /> Change in Settings
          </button>
        </div>
      )}
    </div>
  )
}
