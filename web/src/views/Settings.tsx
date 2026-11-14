import { useEffect, useState, type ReactNode } from 'react'
import { Download, HardDrive } from 'lucide-react'
import { api, type Language } from '../lib/api'
import { useAsync } from '../lib/hooks'
import { hasVoice } from '../lib/speech'
import { languageName } from '../lib/rtl'
import { useNav } from '../state/nav'
import { useSettings, type Settings as S } from '../state/settings'
import { ErrorNote, Field, Loading, Screen, SectionLabel, Segmented, Toggle, inputCls } from '../components/ui'
import { PlayButton } from '../components/PlayButton'

const SAMPLE: Record<string, string> = {
  fa: 'سلام، حال شما چطور است؟', ar: 'مرحبا، كيف حالك؟', de: 'Hallo, wie geht es dir?', it: 'Ciao, come stai?',
  nl: 'Hallo, hoe gaat het?', ru: 'Привет, как дела?', fr: 'Bonjour, comment ça va ?', es: 'Hola, ¿qué tal?', en: 'Hello, how are you?',
}

export default function Settings() {
  const nav = useNav()
  const { settings, update, pair, setPair } = useSettings()
  const langs = useAsync('languages', () => api.languages())
  const health = useAsync('health', () => api.health())
  const sources = useAsync('materials', () => api.materialsSources())

  return (
    <Screen title="Settings" onBack={nav.close}>
      <div className="mx-auto w-full max-w-2xl space-y-10 px-4 pb-20 pt-6">
        <Group title="Languages">
          {langs.error && <ErrorNote error={langs.error} onRetry={langs.reload} />}
          <div className="grid gap-4 sm:grid-cols-3">
            <LangSelect label="I speak" value={pair.source} langs={langs.data} onChange={(v) => setPair({ ...pair, source: v })} />
            <LangSelect label="I’m learning" value={pair.target} langs={langs.data} onChange={(v) => setPair({ ...pair, target: v })} />
            <LangSelect label="Explanations in" value={pair.support} langs={langs.data} onChange={(v) => setPair({ ...pair, support: v })} />
          </div>
          {pair.source === pair.target && <p className="mt-3 text-[13px] text-danger">Pick a language to learn that’s different from your own.</p>}
        </Group>

        <Group title="Reading">
          <div className="py-3">
            <p className="mb-2 text-[15px] text-ink">Script display</p>
            <Segmented<S['script']>
              label="Script display"
              value={settings.script}
              onChange={(v) => update({ script: v })}
              options={[
                { value: 'both', label: 'Both' },
                { value: 'script', label: 'Script only' },
                { value: 'tr', label: 'Transliteration' },
              ]}
            />
          </div>
          <Toggle
            label="Show translations by default"
            description="Otherwise tap a line to see its meaning."
            checked={settings.showGloss}
            onChange={(v) => update({ showGloss: v })}
          />
        </Group>

        <Group title="Speech">
          <div className="py-3">
            <p className="mb-2 text-[15px] text-ink">Voice</p>
            <Segmented<S['voice']>
              label="Voice"
              value={settings.voice}
              onChange={(v) => update({ voice: v })}
              options={[
                { value: 'auto', label: 'Automatic' },
                { value: 'browser', label: 'This device only' },
                { value: 'off', label: 'Off' },
              ]}
            />
            <p className="mt-2 text-[13px] text-ink-3">Automatic uses the server’s voice when one is installed, otherwise this device’s.</p>
          </div>
          <div className="py-3">
            <p className="mb-2 text-[15px] text-ink">Speed</p>
            <Segmented
              label="Speech speed"
              value={String(settings.rate)}
              onChange={(v) => update({ rate: v === '0.75' ? 0.75 : 1 })}
              options={[{ value: '0.75', label: 'Slower' }, { value: '1', label: 'Normal' }]}
            />
          </div>
          <VoiceCheck lang={pair.target} voice={settings.voice} />
        </Group>

        <Group title="Goals">
          <div className="py-3">
            <p className="mb-2 text-[15px] text-ink">Daily goal</p>
            <Segmented
              label="Daily goal"
              value={String(settings.dailyGoal)}
              onChange={(v) => update({ dailyGoal: Number(v) as S['dailyGoal'] })}
              options={[5, 10, 15, 20].map((m) => ({ value: String(m), label: `${m} min` }))}
            />
          </div>
          <Toggle label="Show streak" description="Days in a row with some practice." checked={settings.showStreak} onChange={(v) => update({ showStreak: v })} />
        </Group>

        <Group title="AI provider">
          {health.loading && !health.data && <Loading />}
          {health.error && <ErrorNote error={health.error} onRetry={health.reload} />}
          {health.data && (
            <p className="text-[15px] text-ink">
              {health.data.ai_provider} <span className="text-ink-3">· lingua-agent {health.data.version}</span>
            </p>
          )}
          <p className="mt-1 text-[13px] text-ink-3">Configured with environment variables on the server. See docs/providers.md.</p>
        </Group>

        <Group title="Material sources">
          {sources.loading && !sources.data && <Loading />}
          {sources.error && <ErrorNote error={sources.error} onRetry={sources.reload} />}
          {sources.data?.length === 0 && <p className="text-sm text-ink-3">No sources configured. Add one with <code className="text-[13px]">lingua-agent materials add</code>.</p>}
          {sources.data && sources.data.length > 0 && (
            <ul className="divide-y divide-line border-y border-line">
              {sources.data.map((s) => (
                <li key={s.name} className="flex items-start gap-3 py-3">
                  <HardDrive size={18} className="mt-0.5 shrink-0 text-ink-3" aria-hidden />
                  <div className="min-w-0 flex-1">
                    <p className="text-[15px] text-ink">{s.name}</p>
                    <p className="truncate text-[13px] text-ink-3">{s.provider} · {s.root}</p>
                    {s.notes && <p className="text-[13px] text-ink-3">{s.notes}</p>}
                  </div>
                  <span className={`shrink-0 text-[13px] ${s.available ? 'text-accent' : 'text-ink-3'}`}>
                    {s.available ? 'Available' : 'Offline'}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Group>

        <Group title="Your data">
          <a
            href={api.exportAnkiUrl(pair.target)}
            className="inline-flex h-11 items-center gap-2 rounded-xl border border-line-strong bg-surface px-4 text-[15px] text-ink hover:bg-surface-2"
          >
            <Download size={18} aria-hidden /> Export {languageName(pair.target)} cards for Anki
          </a>
          <p className="mt-2 text-[13px] text-ink-3">Settings are stored in this browser.</p>
        </Group>
      </div>
    </Screen>
  )
}

function Group({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section>
      <SectionLabel>{title}</SectionLabel>
      <div className="divide-y divide-line/0">{children}</div>
    </section>
  )
}

function LangSelect({ label, value, langs, onChange }: {
  label: string
  value: string
  langs: Language[] | undefined
  onChange: (v: string) => void
}) {
  const options = langs ?? [{ code: value, name: languageName(value), native_name: '', script: '', direction: 'ltr', transliteration_supported: false } as Language]
  return (
    <Field label={label}>
      <select className={inputCls} value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((l) => (
          <option key={l.code} value={l.code}>
            {l.name}{l.native_name && l.native_name !== l.name ? ` · ${l.native_name}` : ''}
          </option>
        ))}
      </select>
    </Field>
  )
}

function VoiceCheck({ lang, voice }: { lang: string; voice: S['voice'] }) {
  const [ok, setOk] = useState<boolean | null>(null)
  useEffect(() => {
    let alive = true
    hasVoice(lang).then((v) => { if (alive) setOk(v) })
    return () => { alive = false }
  }, [lang, voice])
  if (voice === 'off') return null
  return (
    <div className="flex items-center justify-between gap-3 py-3">
      <p className="text-[13px] text-ink-2">
        {ok === null ? 'Checking voices' : ok
          ? `A ${languageName(lang)} voice is available.`
          : `No ${languageName(lang)} voice found. Install one in your system’s text-to-speech settings, or set up a server voice.`}
      </p>
      {ok && <PlayButton text={SAMPLE[lang] ?? 'Hello'} lang={lang} label="Play a sample" />}
    </div>
  )
}
