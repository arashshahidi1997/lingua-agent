import { Fragment, type ReactNode } from 'react'

// Just enough markdown for lesson notes: paragraphs, "- " bullet lists,
// **bold**, *italic* / _italic_ and `code`. No HTML is ever injected.
// Runs of Arabic-script text (Persian examples in an English note) get their own lang + dir, so they
// pick up the Persian font and don't scramble the direction of the sentence around them.

const RTL_RUN = /[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]+(?:[\s\u200C.،؟!:«»()-]*[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]+)*/g

function runs(text: string, keyBase: string, rtlLang: string): ReactNode[] {
  const out: ReactNode[] = []
  let last = 0
  let i = 0
  for (const m of text.matchAll(RTL_RUN)) {
    const at = m.index ?? 0
    if (at > last) out.push(text.slice(last, at))
    out.push(
      <span key={`${keyBase}-r${i++}`} lang={rtlLang} dir="rtl" className="font-fa" style={{ lineHeight: 'inherit', unicodeBidi: 'isolate' }}>
        {m[0]}
      </span>,
    )
    last = at + m[0].length
  }
  if (last < text.length) out.push(text.slice(last))
  return out
}

function inline(text: string, keyBase: string, rtlLang: string): ReactNode[] {
  const out: ReactNode[] = []
  const re = /(\*\*[^*]+\*\*|\*[^*\s][^*]*\*|_[^_\s][^_]*_|`[^`]+`)/g
  let last = 0
  let m: RegExpExecArray | null
  let i = 0
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(...runs(text.slice(last, m.index), `${keyBase}-t${i}`, rtlLang))
    const tok = m[0]
    const k = `${keyBase}-${i++}`
    if (tok.startsWith('**')) out.push(<strong key={k} className="font-semibold text-ink">{runs(tok.slice(2, -2), k, rtlLang)}</strong>)
    else if (tok.startsWith('`')) out.push(<code key={k} className="rounded bg-surface-2 px-1 text-[0.9em]">{runs(tok.slice(1, -1), k, rtlLang)}</code>)
    else out.push(<em key={k}>{runs(tok.slice(1, -1), k, rtlLang)}</em>)
    last = m.index + tok.length
  }
  if (last < text.length) out.push(...runs(text.slice(last), `${keyBase}-t${i}`, rtlLang))
  return out
}

/** `rtlLang`: the language to tag Arabic-script runs with (the course's target when it is written that way). */
export function Markdown({ text, className = '', rtlLang = 'fa' }: { text: string; className?: string; rtlLang?: string }) {
  const blocks = text.trim().split(/\n\s*\n/)
  return (
    <div className={`space-y-3 ${className}`}>
      {blocks.map((block, bi) => {
        const lines = block.split('\n')
        if (lines.every((l) => /^\s*[-*]\s+/.test(l))) {
          return (
            <ul key={bi} className="list-disc space-y-1 ps-5">
              {lines.map((l, li) => <li key={li}>{inline(l.replace(/^\s*[-*]\s+/, ''), `${bi}-${li}`, rtlLang)}</li>)}
            </ul>
          )
        }
        const heading = /^#{1,6}\s+(.*)$/.exec(lines[0])
        if (heading && lines.length === 1) {
          return <p key={bi} className="font-semibold text-ink">{inline(heading[1], `${bi}`, rtlLang)}</p>
        }
        return (
          <p key={bi}>
            {lines.map((l, li) => (
              <Fragment key={li}>
                {li > 0 && <br />}
                {inline(l.replace(/^#{1,6}\s+/, ''), `${bi}-${li}`, rtlLang)}
              </Fragment>
            ))}
          </p>
        )
      })}
    </div>
  )
}
