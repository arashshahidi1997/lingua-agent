import { Fragment, type ReactNode } from 'react'

// Just enough markdown for lesson notes: paragraphs, "- " bullet lists,
// **bold**, *italic* / _italic_ and `code`. No HTML is ever injected.

function inline(text: string, keyBase: string): ReactNode[] {
  const out: ReactNode[] = []
  const re = /(\*\*[^*]+\*\*|\*[^*\s][^*]*\*|_[^_\s][^_]*_|`[^`]+`)/g
  let last = 0
  let m: RegExpExecArray | null
  let i = 0
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index))
    const tok = m[0]
    const k = `${keyBase}-${i++}`
    if (tok.startsWith('**')) out.push(<strong key={k} className="font-semibold text-ink">{tok.slice(2, -2)}</strong>)
    else if (tok.startsWith('`')) out.push(<code key={k} className="rounded bg-surface-2 px-1 text-[0.9em]">{tok.slice(1, -1)}</code>)
    else out.push(<em key={k}>{tok.slice(1, -1)}</em>)
    last = m.index + tok.length
  }
  if (last < text.length) out.push(text.slice(last))
  return out
}

export function Markdown({ text, className = '' }: { text: string; className?: string }) {
  const blocks = text.trim().split(/\n\s*\n/)
  return (
    <div className={`space-y-3 ${className}`}>
      {blocks.map((block, bi) => {
        const lines = block.split('\n')
        if (lines.every((l) => /^\s*[-*]\s+/.test(l))) {
          return (
            <ul key={bi} className="list-disc space-y-1 ps-5">
              {lines.map((l, li) => <li key={li}>{inline(l.replace(/^\s*[-*]\s+/, ''), `${bi}-${li}`)}</li>)}
            </ul>
          )
        }
        const heading = /^#{1,6}\s+(.*)$/.exec(lines[0])
        if (heading && lines.length === 1) {
          return <p key={bi} className="font-semibold text-ink">{inline(heading[1], `${bi}`)}</p>
        }
        return (
          <p key={bi}>
            {lines.map((l, li) => (
              <Fragment key={li}>
                {li > 0 && <br />}
                {inline(l.replace(/^#{1,6}\s+/, ''), `${bi}-${li}`)}
              </Fragment>
            ))}
          </p>
        )
      })}
    </div>
  )
}
