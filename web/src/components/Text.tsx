// Target-language text, rendered with the right lang/dir/font and the
// learner's display settings (script / transliteration / gloss).

import { useState } from 'react'
import { dirOf } from '../lib/rtl'
import { scriptView } from '../lib/script'
import { useSettings } from '../state/settings'

/**
 * Any short piece of target-language text (a choice, a tile, a title, a correction): lang + dir set, and
 * the learner's script-display setting applied. Without `tr` it shows the script whatever the setting.
 * `stack` puts the transliteration on its own line under the script; otherwise it follows inline.
 */
export function Target({ text, tr, lang, className = '', trClassName = 'text-[0.8em] text-ink-3', stack = false, hideTr = false }: {
  text: string
  tr?: string | null
  lang: string
  className?: string
  trClassName?: string
  stack?: boolean
  hideTr?: boolean
}) {
  const { settings } = useSettings()
  const v = scriptView(settings.script, tr, hideTr)
  const dir = dirOf(lang)
  if (v.trIsMain) return <span dir="ltr" className={`${className} [unicode-bidi:isolate]`}>{tr}</span>
  const script = <span lang={lang} dir={dir} className={`${className} [unicode-bidi:isolate]`}>{text}</span>
  if (!v.showTr) return script
  if (stack) {
    return (
      <span className="inline-flex flex-col">
        {script}
        <span dir="ltr" className={`${trClassName} leading-snug`}>{tr}</span>
      </span>
    )
  }
  return <>{script}<span className={trClassName}> · <span dir="ltr" className="[unicode-bidi:isolate]">{tr}</span></span></>
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

  // A question that hides the transliteration tests reading the script, so the script always shows.
  const { showScript, showTr, trIsMain } = scriptView(settings.script, tr, hideTr)

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
