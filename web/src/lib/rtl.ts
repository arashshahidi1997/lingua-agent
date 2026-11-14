// Direction and locale helpers for rendering target-language text correctly.
// Source of truth is the backend's /api/languages, but we keep a tiny
// LTR/RTL map so we can wrap text without round-tripping every render.

const RTL_CODES = new Set(['fa', 'ar', 'he', 'ur', 'ps', 'sd'])

export function dirOf(code: string): 'ltr' | 'rtl' {
  return RTL_CODES.has(code) ? 'rtl' : 'ltr'
}

export function isRtl(code: string): boolean {
  return dirOf(code) === 'rtl'
}

/** `lang` + `dir` attributes for an element holding text in `code`. */
export function langAttrs(code: string): { lang: string; dir: 'ltr' | 'rtl' } {
  return { lang: code, dir: dirOf(code) }
}

const BCP47: Record<string, string> = {
  fa: 'fa-IR', ar: 'ar-SA', he: 'he-IL', ur: 'ur-PK', en: 'en-US', de: 'de-DE', it: 'it-IT',
  nl: 'nl-NL', fr: 'fr-FR', es: 'es-ES', pt: 'pt-PT', ru: 'ru-RU', uk: 'uk-UA', tr: 'tr-TR',
}

/** A full locale tag for speech APIs (fa → fa-IR). */
export function bcp47(code: string): string {
  return BCP47[code] ?? code
}

const SHORT: Record<string, string> = { fa: 'فا', ar: 'عر', ur: 'ار', he: 'עב', ru: 'РУ', uk: 'УК' }

/** Compact label for the pair chip: "EN", "فا". */
export function shortLabel(code: string): string {
  return SHORT[code] ?? code.toUpperCase()
}

const NAMES: Record<string, string> = {
  fa: 'Persian', ar: 'Arabic', en: 'English', de: 'German', it: 'Italian', nl: 'Dutch',
  fr: 'French', es: 'Spanish', ru: 'Russian', pt: 'Portuguese', tr: 'Turkish',
}

export function languageName(code: string): string {
  return NAMES[code] ?? code.toUpperCase()
}
