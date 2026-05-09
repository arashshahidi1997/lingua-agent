import { useEffect, useRef, useState } from 'react'
import { api, type SessionMessage, type TutorSession } from '../lib/api'
import { useLangPair } from '../state/LangPair'
import { isRtl } from '../lib/rtl'
import { Button, Card, ErrorBanner, Loading, Section } from '../components/ui'

export default function Tutor() {
  const { pair } = useLangPair()
  const [session, setSession] = useState<TutorSession | null>(null)
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Open a fresh session whenever the language pair changes.
  useEffect(() => {
    setSession(null); setError(null)
    api.openSession({
      source_language: pair.source,
      target_language: pair.target,
      support_language: pair.support,
    }).then(setSession).catch((e) => setError(String(e)))
  }, [pair.source, pair.target, pair.support])

  // Auto-scroll to the bottom on new messages.
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [session?.messages.length])

  const send = async () => {
    if (!session || !input.trim()) return
    const content = input.trim()
    setInput(''); setBusy(true); setError(null)

    // Optimistic append.
    const optimistic: SessionMessage = {
      role: 'user', content, created_at: new Date().toISOString(),
    }
    setSession({ ...session, messages: [...session.messages, optimistic] })

    try {
      const reply = await api.sendMessage(session.id, content)
      const assistantMsg: SessionMessage = {
        role: 'assistant', content: reply.content, created_at: reply.created_at,
      }
      setSession((s) => s && ({ ...s, messages: [...s.messages, assistantMsg] }))
    } catch (e) {
      setError(String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Section title="Tutor chat">
      <ErrorBanner error={error} />
      {!session && !error && <Loading label="Opening session…" />}
      {session && (
        <>
          <Card>
            <div ref={scrollRef} className="max-h-[60vh] min-h-[20rem] space-y-3 overflow-y-auto">
              {session.messages.length === 0 && (
                <p className="text-sm text-slate-500">
                  Say hi to start. The tutor uses the configured AI provider; with{' '}
                  <code>provider=mock</code> you'll see canned responses.
                </p>
              )}
              {session.messages.map((m, i) => (
                <MessageBubble key={i} m={m} sourceLang={pair.source} targetLang={pair.target} />
              ))}
            </div>
          </Card>
          <Card>
            <div className="flex gap-2">
              <input
                className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm"
                placeholder="Ask the tutor…"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
                disabled={busy}
              />
              <Button onClick={send} disabled={busy || !input.trim()}>{busy ? 'Sending…' : 'Send'}</Button>
            </div>
            <p className="mt-2 text-xs text-slate-500">
              Session <span className="font-mono">{session.id}</span> · pair {session.source_language}→{session.target_language}
            </p>
          </Card>
        </>
      )}
    </Section>
  )
}

function MessageBubble({ m, sourceLang, targetLang }: {
  m: SessionMessage; sourceLang: string; targetLang: string
}) {
  const isUser = m.role === 'user'
  // Heuristic: user messages render in source-language direction; assistant in
  // target-language direction. Good enough for the mock; real assistants will
  // mix languages and we can refine later.
  const dir = (isUser ? isRtl(sourceLang) : isRtl(targetLang)) ? 'rtl' : 'ltr'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        dir={dir}
        className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
          isUser
            ? 'bg-violet-600 text-white'
            : m.role === 'assistant'
              ? 'bg-slate-100 text-slate-900'
              : 'bg-amber-50 text-amber-900'
        }`}
      >
        {m.content}
      </div>
    </div>
  )
}
