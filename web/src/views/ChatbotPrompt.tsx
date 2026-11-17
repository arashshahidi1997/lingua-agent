import { useState } from 'react'
import { Check, Copy, ExternalLink } from 'lucide-react'
import { courseApi } from '../lib/course-api'
import { useAsync } from '../lib/hooks'
import { languageName } from '../lib/rtl'
import { useNav } from '../state/nav'
import { useSettings } from '../state/settings'
import { Button, ErrorNote, Loading, Screen, SectionLabel, Segmented } from '../components/ui'
import { Target } from '../components/Text'
import { PlayButton } from '../components/PlayButton'

// A role-play to practise in the learner's own AI chatbot: the app writes the prompt (scenario, character,
// the unit's words, how to correct), the learner copies it into ChatGPT, Claude, Gemini or another chatbot,
// typing or in its voice mode.

const CHATBOTS = [
  { name: 'ChatGPT', url: 'https://chatgpt.com/' },
  { name: 'Claude', url: 'https://claude.ai/new' },
  { name: 'Gemini', url: 'https://gemini.google.com/app' },
]

type Mode = 'text' | 'voice'

async function copy(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    return false
  }
}

export default function ChatbotPrompt({ scenarioId }: { scenarioId: string }) {
  const nav = useNav()
  const { pair } = useSettings()
  const [mode, setMode] = useState<Mode>('text')
  const [copied, setCopied] = useState(false)
  const [copyFailed, setCopyFailed] = useState(false)
  const scenario = useAsync(`scenario|${scenarioId}`, () => courseApi.scenario(scenarioId))
  const prompt = useAsync(`scenario-prompt|${scenarioId}|${mode}`, () => courseApi.scenarioPrompt(scenarioId, mode === 'voice'))
  const sc = scenario.data
  const text = prompt.data?.prompt ?? ''

  const doCopy = async () => {
    const ok = await copy(text)
    setCopied(ok)
    setCopyFailed(!ok)
    if (ok) window.setTimeout(() => setCopied(false), 2500)
    return ok
  }

  const openIn = async (url: string) => {
    // Open first (a popup must start from the tap itself), then copy into the clipboard.
    window.open(url, '_blank', 'noopener')
    await doCopy()
  }

  return (
    <Screen title={sc?.title ?? 'Role-play'} onBack={nav.close} label="Role-play prompt">
      <div className="mx-auto w-full max-w-2xl px-4 pb-16 pt-6">
        {scenario.loading && !sc && <Loading />}
        <ErrorNote error={scenario.error} onRetry={scenario.reload} />
        {sc && (
          <>
            <p className="text-[13px] font-medium uppercase tracking-[0.08em] text-ink-3">Role-play</p>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight">
              {sc.title} <span className="font-normal text-ink-3">· <Target text={sc.title_target} lang={pair.target} /></span>
            </h1>
            <p className="mt-3 text-[15px] text-ink-2">{sc.setting}</p>
            <p className="mt-2 text-[15px] text-ink"><span className="text-ink-3">Your goal · </span>{sc.goal}</p>

            <SectionLabel className="mt-8">Practise it with your AI chatbot</SectionLabel>
            <p className="text-[15px] text-ink-2">
              Copy this prompt into the chatbot you use. It plays the character in simple {languageName(pair.target)}, corrects you gently, and sums
              up when you say “end”.
            </p>
            <div className="mt-4">
              <Segmented<Mode>
                label="How you'll talk"
                value={mode}
                onChange={setMode}
                options={[{ value: 'text', label: 'Typing' }, { value: 'voice', label: 'Voice chat' }]}
              />
              <p className="mt-2 text-[13px] text-ink-3">
                {mode === 'voice'
                  ? `For a voice mode: the character only speaks ${languageName(pair.target)}, without transliteration or translations read aloud. Paste it, then switch the chatbot to voice.`
                  : `Each reply comes as ${languageName(pair.target)}, transliteration and meaning, with a “Better:” line when you make a mistake.`}
              </p>
            </div>

            <div className="mt-5 flex flex-wrap gap-2">
              <Button onClick={() => void doCopy()} disabled={!text}>
                {copied ? <Check size={18} /> : <Copy size={18} />} {copied ? 'Copied' : 'Copy prompt'}
              </Button>
              {CHATBOTS.map((c) => (
                <Button key={c.name} variant="secondary" disabled={!text} onClick={() => void openIn(c.url)}>
                  {c.name} <ExternalLink size={15} />
                </Button>
              ))}
            </div>
            <p className="mt-2 text-[13px] text-ink-3" role="status">
              {copyFailed
                ? 'Couldn’t copy automatically. Select the prompt below and copy it.'
                : copied ? 'Copied. Paste it into a new chat.' : 'The chatbot buttons copy the prompt and open a new chat.'}
            </p>

            {prompt.loading && !prompt.data && <Loading />}
            <ErrorNote error={prompt.error} onRetry={prompt.reload} />
            {text && (
              <pre
                dir="auto"
                className="mt-4 max-h-80 overflow-auto whitespace-pre-wrap rounded-2xl border border-line bg-surface p-4 font-sans text-[13px] leading-relaxed text-ink-2 select-all"
              >
                {text}
              </pre>
            )}

            {sc.useful.length > 0 && (
              <>
                <SectionLabel className="mt-8">Useful phrases</SectionLabel>
                <ul className="divide-y divide-line">
                  {[sc.opener, ...sc.useful].map((p) => (
                    <li key={p.id} className="flex items-center gap-3 py-3">
                      <PlayButton text={p.text} lang={pair.target} size="sm" />
                      <div className="min-w-0 flex-1">
                        <Target text={p.text} tr={p.tr} lang={pair.target} stack className="text-[18px]" />
                        <p className="text-[13px] text-ink-3">{p.gloss}</p>
                      </div>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </>
        )}
      </div>
    </Screen>
  )
}
