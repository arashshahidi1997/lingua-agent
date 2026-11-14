import { useEffect, useRef, useState } from 'react'
import { Square, Volume2 } from 'lucide-react'
import { speak, stopSpeech, playUrl } from '../lib/speech'
import { useSettings } from '../state/settings'

/** Speaks `text` in `lang` (or plays `url`). Tap again to stop. */
export function PlayButton({ text, lang, url, size = 'md', label, tone = 'accent', pitch }: {
  text?: string
  lang?: string
  url?: string
  size?: 'sm' | 'md' | 'lg'
  label?: string
  tone?: 'accent' | 'plain' | 'solid'
  pitch?: number
}) {
  const { settings } = useSettings()
  const [playing, setPlaying] = useState(false)
  const alive = useRef(true)
  useEffect(() => {
    alive.current = true
    return () => { alive.current = false }
  }, [])

  if (settings.voice === 'off' && !url) return null

  const onClick = async () => {
    if (playing) { stopSpeech(); setPlaying(false); return }
    setPlaying(true)
    try {
      if (url) await playUrl(url)
      else if (text && lang) await speak(text, lang, { pitch })
    } catch {
      // nothing to play; the speech module already hinted
    } finally {
      if (alive.current) setPlaying(false)
    }
  }

  const dims = { sm: 'h-8 w-8', md: 'h-10 w-10', lg: 'h-16 w-16' }[size]
  const icon = { sm: 16, md: 18, lg: 26 }[size]
  const tones = {
    accent: 'text-accent hover:bg-accent-soft',
    plain: 'text-ink-2 hover:bg-surface-2',
    solid: 'bg-accent text-accent-ink hover:bg-accent-strong',
  }[tone]
  const name = label ?? (text ? `Play “${text}”` : 'Play')
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={playing ? 'Stop' : name}
      title={playing ? 'Stop' : 'Play'}
      className={`inline-flex shrink-0 items-center justify-center rounded-full transition-colors ${dims} ${tones}`}
    >
      {playing ? <Square size={icon - 4} fill="currentColor" /> : <Volume2 size={icon} />}
    </button>
  )
}
