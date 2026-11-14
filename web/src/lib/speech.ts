// One place for making the app speak.
//
// speak(text, lang) tries, in order:
//   1. the server voice (GET /api/tts) when the voice setting is "auto" and
//      /api/speech says a server voice exists for the language;
//   2. the browser's speechSynthesis with a voice matching the language;
//   3. nothing: it resolves silently and notifies hint listeners once per
//      language, so the UI can say "No voice for Persian on this device".
//
// Every call returns a promise that resolves when playback ends (or is
// stopped), which Play all and shadowing rely on.

import { courseApi, type SpeechInfo } from './course-api'
import { bcp47, languageName } from './rtl'

export type VoiceMode = 'auto' | 'browser' | 'off'

interface SpeechConfig { mode: VoiceMode; rate: number }

let config: SpeechConfig = { mode: 'auto', rate: 1 }

export function configureSpeech(next: SpeechConfig) {
  config = next
}

// ---- server capabilities ---------------------------------------------------

let speechInfo: Promise<SpeechInfo | null> | null = null

export function getSpeechInfo(): Promise<SpeechInfo | null> {
  if (!speechInfo) speechInfo = courseApi.speech().catch(() => null)
  return speechInfo
}

// ---- browser voices ----------------------------------------------------------

function synth(): SpeechSynthesis | null {
  return typeof window !== 'undefined' && 'speechSynthesis' in window ? window.speechSynthesis : null
}

let voicesReady: Promise<SpeechSynthesisVoice[]> | null = null

function loadVoices(): Promise<SpeechSynthesisVoice[]> {
  const s = synth()
  if (!s) return Promise.resolve([])
  const now = s.getVoices()
  if (now.length) return Promise.resolve(now)
  if (!voicesReady) {
    voicesReady = new Promise((resolve) => {
      const done = () => resolve(s.getVoices())
      s.addEventListener('voiceschanged', done, { once: true })
      window.setTimeout(done, 1200)
    })
  }
  return voicesReady
}

async function browserVoice(lang: string): Promise<SpeechSynthesisVoice | null> {
  const voices = await loadVoices()
  const full = bcp47(lang).toLowerCase()
  const short = lang.toLowerCase()
  return (
    voices.find((v) => v.lang.toLowerCase().replace('_', '-') === full) ??
    voices.find((v) => v.lang.toLowerCase().startsWith(short)) ??
    null
  )
}

/** Whether some voice (server or browser) exists for a language. */
export async function hasVoice(lang: string): Promise<boolean> {
  if (config.mode === 'off') return false
  if (config.mode === 'auto') {
    const info = await getSpeechInfo()
    if (info?.server_tts[lang]) return true
  }
  return (await browserVoice(lang)) !== null
}

// ---- hints -------------------------------------------------------------------

type HintListener = (message: string) => void
const hintListeners = new Set<HintListener>()
const hinted = new Set<string>()

export function onSpeechHint(fn: HintListener): () => void {
  hintListeners.add(fn)
  return () => { hintListeners.delete(fn) }
}

function hintNoVoice(lang: string) {
  if (hinted.has(lang)) return
  hinted.add(lang)
  const msg = `No voice for ${languageName(lang)} on this device. You can add one in your system settings, or set up a server voice.`
  hintListeners.forEach((fn) => fn(msg))
}

// ---- playback ------------------------------------------------------------------

let current: { stop: () => void } | null = null

/** Stop whatever is playing (speech or a recording). */
export function stopSpeech() {
  current?.stop()
  current = null
}

/** Play a URL (server TTS, a recording). Resolves when it ends; rejects if it cannot play. */
export function playUrl(url: string, rate = 1): Promise<void> {
  stopSpeech()
  return new Promise<void>((resolve, reject) => {
    const audio = new Audio(url)
    audio.playbackRate = rate
    let settled = false
    const finish = (err?: unknown) => {
      if (settled) return
      settled = true
      if (current?.stop === stop) current = null
      if (err) reject(err)
      else resolve()
    }
    const stop = () => { audio.pause(); finish() }
    current = { stop }
    audio.addEventListener('ended', () => finish())
    audio.addEventListener('error', () => finish(new Error('audio error')))
    audio.play().catch((e) => finish(e))
  })
}

export interface SpeakOptions {
  /** Slight pitch change so two speakers in a dialogue sound different with browser voices. */
  pitch?: number
  rate?: number
}

async function speakBrowser(text: string, lang: string, opts: SpeakOptions): Promise<boolean> {
  const s = synth()
  if (!s) return false
  const voice = await browserVoice(lang)
  if (!voice) return false
  stopSpeech()
  return new Promise<boolean>((resolve) => {
    const u = new SpeechSynthesisUtterance(text)
    u.voice = voice
    u.lang = voice.lang
    u.rate = opts.rate ?? config.rate
    if (opts.pitch) u.pitch = opts.pitch
    let settled = false
    const finish = () => {
      if (settled) return
      settled = true
      if (current?.stop === stop) current = null
      resolve(true)
    }
    const stop = () => { s.cancel(); finish() }
    current = { stop }
    u.onend = finish
    u.onerror = finish
    s.speak(u)
  })
}

/** Speak `text` in language `lang`. Resolves when playback ends (or immediately when there is no voice). */
export async function speak(text: string, lang: string, opts: SpeakOptions = {}): Promise<void> {
  if (!text.trim() || config.mode === 'off') return
  if (config.mode === 'auto') {
    const info = await getSpeechInfo()
    if (info?.server_tts[lang]) {
      try {
        await playUrl(courseApi.ttsUrl(text, lang), opts.rate ?? config.rate)
        return
      } catch {
        // fall through to the browser voice
      }
    }
  }
  const spoke = await speakBrowser(text, lang, opts)
  if (!spoke) hintNoVoice(lang)
}
