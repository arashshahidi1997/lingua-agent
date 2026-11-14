import type { CourseExercise } from './course-api'

// Local grading for exercise sessions (the server ships the answers).

/** Transliteration comparison: lowercase, strip diacritics (â→a), punctuation, spaces, hyphens. */
export function lenientTr(s: string): string {
  return s
    .toLowerCase()
    .normalize('NFD')
    .replace(/\p{M}/gu, '')
    .replace(/[\p{P}\p{S}\s]/gu, '')
}

/** Sentence comparison for word-order tiles: collapse spaces, drop ZWNJ and end punctuation. */
export function normSentence(s: string): string {
  return s
    .replace(/‌/g, '')
    .replace(/[.!?،؟…:;,"«»]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase()
}

/** Deterministic shuffle so renders stay pure (seeded from a string). */
export function seededShuffle<T>(arr: readonly T[], seed: string): T[] {
  let h = 2166136261
  for (let i = 0; i < seed.length; i++) {
    h ^= seed.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  // mulberry32, seeded from the FNV hash
  let t = h >>> 0
  const rand = () => {
    t = (t + 0x6d2b79f5) | 0
    let r = Math.imul(t ^ (t >>> 15), 1 | t)
    r = (r + Math.imul(r ^ (r >>> 7), 61 | r)) ^ r
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296
  }
  const out = arr.slice()
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1))
    ;[out[i], out[j]] = [out[j], out[i]]
  }
  return out
}

export const PROMPTS: Record<CourseExercise['kind'], string> = {
  intro: 'New',
  choose_gloss: 'What does this mean?',
  choose_text: 'How do you say this?',
  listen: 'What do you hear?',
  match: 'Match the pairs',
  order: 'Build the sentence',
  type_tr: 'Type how it sounds',
}

/** Tiles answer → sentence text. */
export function orderText(ex: CourseExercise, answer: string): string {
  if (!answer) return ''
  return answer.split(',').map((i) => ex.tiles[Number(i)]).join(' ')
}

