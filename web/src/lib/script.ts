import type { ScriptDisplay } from '../state/settings'

/**
 * What to show for a piece of target-language text under the script-display setting.
 * Transliteration only replaces the script when there is one to show; `hideTr` (a question that tests
 * reading the script) always keeps the script.
 */
export function scriptView(mode: ScriptDisplay, tr: string | null | undefined, hideTr = false) {
  const hasTr = !!tr && !hideTr
  return {
    showScript: mode !== 'tr' || !hasTr,
    showTr: hasTr && mode !== 'script',
    trIsMain: hasTr && mode === 'tr',
  }
}
