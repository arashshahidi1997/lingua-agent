// Browser speech-to-text (Web Speech API), where available (Chrome / Android).

import { useCallback, useEffect, useRef, useState } from 'react'
import { bcp47 } from './rtl'

interface RecognitionResultEvent {
  results: ArrayLike<ArrayLike<{ transcript: string }> & { isFinal: boolean }>
}

interface Recognition {
  lang: string
  interimResults: boolean
  continuous: boolean
  onresult: ((e: RecognitionResultEvent) => void) | null
  onerror: ((e: { error: string }) => void) | null
  onend: (() => void) | null
  start: () => void
  stop: () => void
  abort: () => void
}

type RecognitionCtor = new () => Recognition

function ctor(): RecognitionCtor | null {
  const w = window as unknown as { SpeechRecognition?: RecognitionCtor; webkitSpeechRecognition?: RecognitionCtor }
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null
}

export function canDictate(): boolean {
  return typeof window !== 'undefined' && ctor() !== null
}

/** Dictation into a text field. onText receives the running transcript. */
export function useDictation(lang: string, onText: (text: string) => void) {
  const [listening, setListening] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const rec = useRef<Recognition | null>(null)
  const cb = useRef(onText)
  useEffect(() => { cb.current = onText })
  useEffect(() => () => rec.current?.abort(), [])

  const start = useCallback(() => {
    const C = ctor()
    if (!C) return
    setError(null)
    const r = new C()
    r.lang = bcp47(lang)
    r.interimResults = true
    r.continuous = false
    r.onresult = (e) => {
      let text = ''
      for (let i = 0; i < e.results.length; i++) text += e.results[i][0].transcript
      cb.current(text)
    }
    r.onerror = (e) => {
      if (e.error !== 'aborted' && e.error !== 'no-speech') {
        setError(e.error === 'not-allowed' ? 'Microphone access was denied.' : 'Speech recognition stopped. Try again or type instead.')
      }
    }
    r.onend = () => setListening(false)
    rec.current = r
    r.start()
    setListening(true)
  }, [lang])

  const stop = useCallback(() => { rec.current?.stop() }, [])

  return { listening, error, start, stop, supported: canDictate() }
}
