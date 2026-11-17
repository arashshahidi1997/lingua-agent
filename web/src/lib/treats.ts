// Milestone treats on the Path (drawn in components/Treats.tsx).

export type TreatKind = 'chai' | 'anaar' | 'peste'

export const TREATS: Record<TreatKind, { fa: string; tr: string; gloss: string }> = {
  chai: { fa: 'چای و نبات', tr: 'chây o nabât', gloss: 'tea with nabat' },
  anaar: { fa: 'انار', tr: 'anâr', gloss: 'pomegranate' },
  peste: { fa: 'پسته', tr: 'peste', gloss: 'pistachios' },
}

/** Tea with nabat at every other milestone; pomegranate and pistachios take turns in between. */
export function treatFor(milestone: number): TreatKind {
  if (milestone % 2 === 0) return 'chai'
  return milestone % 4 === 1 ? 'anaar' : 'peste'
}
