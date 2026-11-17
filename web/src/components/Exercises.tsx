// One component per exercise kind. They are controlled by the Player:
// `answer` is the learner's current answer (a string), `onAnswer` updates it,
// and `locked` is true once the answer has been checked.

import { useState } from 'react'
import { Check } from 'lucide-react'
import type { CourseExercise, Item } from '../lib/course-api'
import { seededShuffle } from '../lib/grading'
import { dirOf } from '../lib/rtl'
import { ItemText, Target } from './Text'
import { PlayButton } from './PlayButton'

export interface ExerciseProps {
  ex: CourseExercise
  lang: string
  support: string
  answer: string
  onAnswer: (a: string) => void
  locked: boolean
  /** Transliteration of a target-language string from this session (choices, tiles), when known. */
  trOf: (text: string) => string | null
}

export function ExerciseBody(props: ExerciseProps) {
  switch (props.ex.kind) {
    case 'intro': return <Intro {...props} />
    case 'choose_gloss': return <ChooseGloss {...props} />
    case 'choose_text': return <ChooseText {...props} />
    case 'listen': return <Listen {...props} />
    case 'order': return <Order {...props} />
    case 'type_tr': return <TypeTr {...props} />
    case 'match': return null // rendered by <Match>, which needs its own state callback
  }
}

function Intro({ ex, lang, support }: ExerciseProps) {
  const it = ex.item!
  return (
    <div className="flex flex-col items-center gap-6 pt-6 text-center">
      <ItemText text={it.text} tr={it.tr} gloss={it.gloss} lang={lang} supportLang={support} size="xl" glossMode="show" align="center" />
      <PlayButton text={it.text} lang={lang} size="lg" tone="solid" />
      {it.note && <p className="max-w-sm text-sm text-ink-2">{it.note}</p>}
    </div>
  )
}

function ChooseGloss({ ex, lang, support, answer, onAnswer, locked }: ExerciseProps) {
  const it = ex.item!
  return (
    <div>
      <div className="flex flex-col items-center gap-3 pb-8 pt-4">
        <ItemText text={it.text} tr={it.tr} lang={lang} size="xl" glossMode="hide" align="center" hideTr={ex.hide_tr} />
        <PlayButton text={it.text} lang={lang} size="sm" />
      </div>
      <Choices choices={ex.choices} lang={support} answer={answer} correct={ex.answer} onAnswer={onAnswer} locked={locked} />
    </div>
  )
}

function ChooseText({ ex, lang, support, answer, onAnswer, locked, trOf }: ExerciseProps) {
  const it = ex.item!
  return (
    <div>
      <p lang={support} className="pb-8 pt-4 text-center text-2xl font-medium text-ink">{it.gloss}</p>
      <Choices choices={ex.choices} lang={lang} answer={answer} correct={ex.answer} onAnswer={onAnswer} locked={locked}
        target trOf={ex.hide_tr ? undefined : trOf} />
    </div>
  )
}

function Listen({ ex, lang, answer, onAnswer, locked, trOf }: ExerciseProps) {
  const it = ex.item!
  return (
    <div>
      <div className="flex justify-center pb-8 pt-4">
        <PlayButton text={it.text} lang={lang} size="lg" tone="solid" label="Play again" />
      </div>
      <Choices choices={ex.choices} lang={lang} answer={answer} correct={ex.answer} onAnswer={onAnswer} locked={locked}
        target trOf={ex.hide_tr ? undefined : trOf} />
    </div>
  )
}

function Choices({ choices, lang, answer, correct, onAnswer, locked, target, trOf }: {
  choices: string[]
  lang: string
  answer: string
  correct: string | null
  onAnswer: (a: string) => void
  locked: boolean
  target?: boolean
  trOf?: (text: string) => string | null
}) {
  const dir = dirOf(lang)
  return (
    <div role="radiogroup" aria-label="Choices" className="grid gap-2.5">
      {choices.map((c, i) => {
        const selected = answer === c
        const isRight = locked && c === correct
        const isWrong = locked && selected && c !== correct
        const tone = isRight
          ? 'border-accent bg-accent-soft text-ink'
          : isWrong
            ? 'border-danger bg-danger-soft text-ink'
            : selected
              ? 'border-accent bg-accent-soft text-ink'
              : 'border-line-strong bg-surface text-ink hover:bg-surface-2'
        return (
          <button
            key={`${i}-${c}`}
            type="button"
            role="radio"
            aria-checked={selected}
            disabled={locked}
            onClick={() => onAnswer(c)}
            className={`flex min-h-14 items-center gap-3 rounded-2xl border px-4 py-2.5 text-start transition-colors disabled:cursor-default ${tone}`}
          >
            <span aria-hidden className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-line text-[12px] text-ink-3">
              {i + 1}
            </span>
            <span className="min-w-0 flex-1">
              {target ? (
                <Target text={c} tr={trOf?.(c)} lang={lang} stack className={dir === 'rtl' ? 'text-2xl' : 'text-lg'} trClassName="text-[13px] text-ink-3" />
              ) : (
                <span lang={lang} dir={dir} className="text-[16px]">{c}</span>
              )}
            </span>
            {isRight && <Check size={18} className="shrink-0 text-accent" aria-label="Correct" />}
          </button>
        )
      })}
    </div>
  )
}

/** Tiles chosen are stored in `answer` as indices joined by ",". */
function Order({ ex, lang, answer, onAnswer, locked }: ExerciseProps) {
  const it = ex.item!
  const dir = dirOf(lang)
  const tileTr = ex.hide_tr ? new Map<string, string>() : wordTr(it.text, it.tr)
  const picked = answer ? answer.split(',').map(Number) : []
  const toggle = (i: number) => {
    if (locked) return
    const next = picked.includes(i) ? picked.filter((x) => x !== i) : [...picked, i]
    onAnswer(next.join(','))
  }
  const tile = 'rounded-xl border px-3.5 py-2 text-xl transition-colors'
  return (
    <div>
      <p className="pb-6 pt-4 text-center text-xl font-medium text-ink">{it.gloss}</p>
      <div
        dir={dir}
        lang={lang}
        aria-label="Your sentence"
        className="flex min-h-16 flex-wrap content-start gap-2 border-b border-line-strong pb-3"
      >
        {picked.map((i) => (
          <button key={i} type="button" onClick={() => toggle(i)} disabled={locked} className={`${tile} border-line-strong bg-surface text-ink`}>
            <Target text={ex.tiles[i]} tr={tileTr.get(ex.tiles[i])} lang={lang} stack trClassName="text-[12px] text-ink-3" />
          </button>
        ))}
      </div>
      <div dir={dir} lang={lang} className="mt-6 flex flex-wrap justify-center gap-2">
        {ex.tiles.map((t, i) => {
          const used = picked.includes(i)
          return (
            <button
              key={i}
              type="button"
              onClick={() => toggle(i)}
              disabled={locked || used}
              aria-hidden={used}
              className={`${tile} ${used ? 'border-line bg-surface-2 text-transparent [&_*]:text-transparent' : 'border-line-strong bg-surface text-ink hover:bg-surface-2'}`}
            >
              <Target text={t} tr={tileTr.get(t)} lang={lang} stack trClassName="text-[12px] text-ink-3" />
            </button>
          )
        })}
      </div>
    </div>
  )
}

function TypeTr({ ex, lang, answer, onAnswer, locked }: ExerciseProps) {
  const it = ex.item!
  return (
    <div>
      <div className="flex flex-col items-center gap-3 pb-8 pt-4">
        <ItemText text={it.text} lang={lang} size="xl" glossMode="hide" align="center" hideTr />
        <PlayButton text={it.text} lang={lang} size="sm" />
      </div>
      <input
        autoFocus
        dir="ltr"
        value={answer}
        disabled={locked}
        onChange={(e) => onAnswer(e.target.value)}
        aria-label="Transliteration"
        placeholder="Type in Latin letters"
        autoCapitalize="off"
        autoCorrect="off"
        autoComplete="off"
        spellCheck={false}
        className="block w-full rounded-2xl border border-line-strong bg-surface px-4 py-3.5 text-center text-xl text-ink placeholder:text-base placeholder:text-ink-3 focus:border-accent focus:outline-none"
      />
    </div>
  )
}

/**
 * Word → transliteration for order tiles, when the sentence and its transliteration split into the same
 * number of words (otherwise the tiles show the script only).
 */
function wordTr(text: string, tr: string | null): Map<string, string> {
  const m = new Map<string, string>()
  if (!tr) return m
  const words = text.trim().split(/\s+/)
  const trs = tr.trim().split(/\s+/)
  if (words.length !== trs.length) return m
  words.forEach((w, i) => { if (!m.has(w)) m.set(w, trs[i]) })
  return m
}

/** Match pairs. Calls onDone with the ids of items that had a wrong attempt once every pair is matched. */
export function Match({ ex, lang, support, locked, onDone }: {
  ex: CourseExercise
  lang: string
  support: string
  locked: boolean
  onDone: (missed: string[]) => void
}) {
  const left = seededShuffle(ex.pairs, `${ex.id}:l`)
  const right = seededShuffle(ex.pairs, `${ex.id}:r`)
  const [sel, setSel] = useState<{ side: 'l' | 'r'; id: string } | null>(null)
  const [matched, setMatched] = useState<string[]>([])
  const [missed, setMissed] = useState<string[]>([])
  const [wrong, setWrong] = useState<string[]>([])

  const tap = (side: 'l' | 'r', item: Item) => {
    if (locked || matched.includes(item.id)) return
    setWrong([])
    if (!sel || sel.side === side) { setSel({ side, id: item.id }); return }
    if (sel.id === item.id) {
      const nextMatched = [...matched, item.id]
      setMatched(nextMatched)
      setSel(null)
      if (nextMatched.length === ex.pairs.length) onDone(missed)
    } else {
      const leftId = side === 'l' ? item.id : sel.id
      setMissed((m) => (m.includes(leftId) ? m : [...m, leftId]))
      setWrong([sel.id, item.id])
      setSel(null)
    }
  }

  const cell = (side: 'l' | 'r', item: Item) => {
    const isMatched = matched.includes(item.id)
    const isSel = sel?.side === side && sel.id === item.id
    const isWrong = wrong.includes(item.id) && !isMatched
    const tone = isMatched
      ? 'border-line bg-surface-2 text-ink-3'
      : isWrong
        ? 'border-danger bg-danger-soft text-ink'
        : isSel
          ? 'border-accent bg-accent-soft text-ink'
          : 'border-line-strong bg-surface text-ink hover:bg-surface-2'
    const l = side === 'l' ? lang : support
    return (
      <button
        key={`${side}-${item.id}`}
        type="button"
        onClick={() => tap(side, item)}
        disabled={isMatched || locked}
        aria-pressed={isSel}
        className={`flex min-h-14 items-center justify-center rounded-2xl border px-3 py-2 text-center transition-colors ${tone}`}
      >
        {side === 'l' ? (
          <Target text={item.text} tr={item.tr} hideTr={ex.hide_tr} lang={lang} stack
            className={dirOf(lang) === 'rtl' ? 'text-xl' : 'text-[15px]'} trClassName="text-[12px] text-ink-3" />
        ) : (
          <span lang={l} dir={dirOf(l)} className="text-[15px]">{item.gloss}</span>
        )}
      </button>
    )
  }

  return (
    <div className="grid grid-cols-2 gap-2.5 pt-4">
      <div className="grid content-start gap-2.5">{left.map((it) => cell('l', it))}</div>
      <div className="grid content-start gap-2.5">{right.map((it) => cell('r', it))}</div>
    </div>
  )
}
