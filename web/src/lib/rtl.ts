// Direction helpers for rendering target-language text correctly.
// Source of truth is the backend's /api/languages, but we cache a tiny
// LTR/RTL map so we can wrap text without round-tripping every render.

const RTL_CODES = new Set(['fa', 'ar', 'he', 'ur', 'ps', 'sd'])

export function dirOf(code: string): 'ltr' | 'rtl' {
  return RTL_CODES.has(code) ? 'rtl' : 'ltr'
}

export function isRtl(code: string): boolean {
  return dirOf(code) === 'rtl'
}
