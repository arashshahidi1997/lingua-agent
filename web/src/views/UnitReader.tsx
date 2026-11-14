import { useState } from 'react'
import { api } from '../lib/api'
import { useAsync } from '../lib/hooks'
import { dirOf } from '../lib/rtl'
import { useNav } from '../state/nav'
import { useSettings } from '../state/settings'
import { ErrorNote, Loading, Screen, SectionLabel, Toggle } from '../components/ui'
import { ItemText } from '../components/Text'
import { PlayButton } from '../components/PlayButton'

/** Reader for a lesson generated from the learner's own text. */
export default function UnitReader({ id }: { id: string }) {
  const nav = useNav()
  const { settings } = useSettings()
  const { data: unit, error, reload } = useAsync(`unit/${id}`, () => api.unitDetail(id))
  const [showAll, setShowAll] = useState(settings.showGloss)

  const target = unit?.target_language ?? 'en'
  const support = unit?.support_language ?? unit?.source_language ?? 'en'
  const dir = dirOf(target)

  return (
    <Screen title={unit?.title ?? 'Lesson'} onBack={nav.close}>
      <div className="mx-auto w-full max-w-2xl px-4 pb-20 pt-6">
        {!unit && !error && <Loading />}
        <ErrorNote error={error} onRetry={reload} />
        {unit && (
          <article className="space-y-10">
            <header>
              <p className="text-[13px] uppercase tracking-[0.08em] text-ink-3">
                {[unit.cefr_level, unit.tags.slice(0, 3).join(', ')].filter(Boolean).join(' · ')}
              </p>
              <h1 className="mt-1 text-[1.75rem] font-semibold leading-tight tracking-tight">{unit.title}</h1>
              {unit.summary && <p className="mt-3 text-[15px] leading-relaxed text-ink-2">{unit.summary}</p>}
            </header>

            {unit.bilingual_reading.length > 0 && (
              <section>
                <div className="mb-2 flex items-center justify-between gap-4">
                  <SectionLabel className="mb-0">Text</SectionLabel>
                  <div className="w-56"><Toggle label="Show translations" checked={showAll} onChange={setShowAll} /></div>
                </div>
                <ol className="divide-y divide-line">
                  {unit.bilingual_reading.map((p, i) => (
                    <li key={i} className="flex items-start gap-2 py-4">
                      <div className="min-w-0 flex-1">
                        <ItemText text={p.target} gloss={p.source} lang={target} supportLang={unit.source_language}
                          size="md" serif={dir === 'ltr'} showGloss={showAll} />
                      </div>
                      <PlayButton text={p.target} lang={target} size="sm" />
                    </li>
                  ))}
                </ol>
              </section>
            )}

            {unit.vocabulary.length > 0 && (
              <section>
                <SectionLabel>Words · {unit.vocabulary.length}</SectionLabel>
                <ul className="divide-y divide-line border-t border-line">
                  {unit.vocabulary.map((v) => {
                    const meaning = (v.translations[support] ?? v.translations[unit.source_language] ?? Object.values(v.translations)[0] ?? []).join(', ')
                    return (
                      <li key={v.id} className="flex items-start gap-2 py-3">
                        <div className="min-w-0 flex-1">
                          <ItemText text={v.lemma} tr={v.transliteration} gloss={meaning || null} lang={target} supportLang={support} size="sm" glossMode="show" />
                          {v.example_text && <p lang={target} dir={dir} className="mt-1 text-[13px] text-ink-3">{v.example_text}</p>}
                        </div>
                        {v.pos && <span className="pt-1 text-[12px] text-ink-3">{v.pos}</span>}
                        <PlayButton text={v.lemma} lang={target} size="sm" />
                      </li>
                    )
                  })}
                </ul>
              </section>
            )}

            {unit.grammar.length > 0 && (
              <section>
                <SectionLabel>Grammar</SectionLabel>
                <div className="space-y-5">
                  {unit.grammar.map((g) => (
                    <div key={g.id}>
                      <h3 className="text-[15px] font-semibold">{g.name}</h3>
                      <p className="mt-1 text-[15px] leading-relaxed text-ink-2">{g.summary}</p>
                      {g.evidence.length > 0 && (
                        <ul className="mt-2 space-y-1 border-s-2 border-line ps-3">
                          {g.evidence.map((ev, i) => (
                            <li key={i} lang={target} dir="auto" className="text-[15px] text-ink">{ev}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                  ))}
                </div>
              </section>
            )}

            {unit.flashcards.length > 0 && (
              <p className="text-[13px] text-ink-3">
                {unit.flashcards.length} flashcards from this lesson are in your review queue.
              </p>
            )}
          </article>
        )}
      </div>
    </Screen>
  )
}
