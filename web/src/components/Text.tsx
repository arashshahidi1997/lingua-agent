// Target-language text, rendered with the right lang/dir/font and the
// learner's display settings (script / transliteration / gloss).

import { useState, type ReactNode } from 'react'
import { dirOf } from '../lib/rtl'
import { useSettings } from '../state/settings'

/** Inline target-language text with lang + dir set (Persian picks up Vazirmatn via [lang]). */
export function Tgt({ lang, children, className = '' }: { lang: string; children: ReactNode; className?: string }) {
  return <span lang={lang} dir={dirOf(lang)} className={className}>{children}</span>
}

const SIZES = {
  sm: { text: 'text-lg', fa: 'text-xl', tr: 'text-[13px]', gloss: 'text-[13px]' },
  md: { text: 'text-xl', fa: 'text-2xl', tr: 'text-sm', gloss: 'text-sm' },
  lg: { text: 'text-2xl', fa: 'text-[1.75rem]', tr: 'text-[15px]', gloss: 'text-[15px]' },
  xl: { text: 'text-3xl', fa: 'text-[2rem] sm:text-[2.25rem]', tr: 'text-base', gloss: 'text-base' },
}

/**
 * Text + transliteration + gloss. `gloss`:
 *  - 'reveal': hidden behind a tap unless `showGloss` (or the setting) is on
 *  - 'show':   always visible
 *  - 'hide':   never shown
 */
export function ItemText({
  text, tr, gloss, lang, supportLang = 'en', size = 'md', glossMode = 'reveal', showGloss,
  align = 'start', serif = false, hideTr = false,
}: {
  text: string
  tr?: string | null
  gloss?: string | null
  lang: string
  supportLang?: string
  size?: keyof typeof SIZES
  glossMode?: 'reveal' | 'show' | 'hide'
  showGloss?: boolean
  align?: 'start' | 'center'
  serif?: boolean
  hideTr?: boolean
}) {
  const { settings } = useSettings()
  const [revealed, setRevealed] = useState(false)
  const dir = dirOf(lang)
  const sz = SIZES[size]
  const scriptCls = dir === 'rtl' ? sz.fa : `${sz.text} ${serif ? 'font-serif' : ''}`

  const mode = settings.script
  const showScript = mode !== 'tr' || !tr
  const showTr = !!tr && !hideTr && mode !== 'script'
  const trIsMain = mode === 'tr' && !!tr

  const glossVisible = glossMode === 'show' || (glossMode === 'reveal' && (showGloss ?? settings.showGloss)) || revealed
  const alignCls = align === 'center' ? 'text-center' : ''

  return (
    <div dir={align === 'center' ? undefined : dir} className={alignCls}>
      {showScript && (
        <div lang={lang} dir={dir} className={`${scriptCls} ${alignCls} leading-snug text-ink`}>{text}</div>
      )}
      {showTr && (
        <div dir="ltr" className={`${trIsMain ? `${sz.text} text-ink` : `${sz.tr} text-ink-3`} ${alignCls} mt-0.5 [unicode-bidi:plaintext]`}>
          {tr}
        </div>
      )}
      {gloss && glossMode !== 'hide' && (
        glossVisible ? (
          <div lang={supportLang} dir={dirOf(supportLang)} className={`${sz.gloss} ${alignCls} mt-1 text-ink-2`}>{gloss}</div>
        ) : (
          <button
            type="button"
            onClick={() => setRevealed(true)}
            className={`mt-1 rounded-md text-[13px] text-ink-3 underline decoration-dotted underline-offset-4 hover:text-ink-2`}
          >
            Show meaning
          </button>
        )
      )}
    </div>
  )
}
