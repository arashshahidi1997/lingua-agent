import { useEffect, useState } from 'react'
import { X } from 'lucide-react'
import { onSpeechHint } from '../lib/speech'

/** One-line notices from non-React modules (for now: "no voice for this language"). */
export function Hints() {
  const [msg, setMsg] = useState<string | null>(null)
  useEffect(() => onSpeechHint(setMsg), [])
  useEffect(() => {
    if (!msg) return
    const t = window.setTimeout(() => setMsg(null), 7000)
    return () => window.clearTimeout(t)
  }, [msg])
  if (!msg) return null
  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-24 z-[60] flex justify-center px-4 md:bottom-8">
      <div role="status" className="anim-in pointer-events-auto flex max-w-md items-start gap-3 rounded-2xl bg-ink px-4 py-3 text-sm text-canvas">
        <span>{msg}</span>
        <button type="button" aria-label="Dismiss" onClick={() => setMsg(null)} className="shrink-0 opacity-70 hover:opacity-100">
          <X size={16} />
        </button>
      </div>
    </div>
  )
}
