// Milestone treats on the Path: a glass of tea with nabat (saffron rock candy), a pomegranate (anâr) and
// pistachios (peste). Hand-drawn inline SVG, flat colours; `earned=false` draws them faded.

import type { TreatKind } from '../lib/treats'

export function Treat({ kind, earned, size = 64 }: { kind: TreatKind; earned: boolean; size?: number }) {
  const style = earned ? undefined : { filter: 'grayscale(1)', opacity: 0.38 }
  return (
    <svg viewBox="0 0 64 64" width={size} height={size} aria-hidden="true" style={style}>
      {kind === 'chai' && <Chai />}
      {kind === 'anaar' && <Anaar />}
      {kind === 'peste' && <Peste />}
    </svg>
  )
}

function Chai() {
  return (
    <g>
      {/* saucer */}
      <ellipse cx="30" cy="55" rx="22" ry="5" fill="#2f4f8a" />
      <ellipse cx="30" cy="54" rx="18" ry="3.6" fill="#f4efe6" />
      <ellipse cx="30" cy="54" rx="9" ry="1.8" fill="#2f4f8a" opacity=".35" />
      {/* nabat stick: a wooden stick with saffron-gold crystals, leaning in the glass */}
      <path d="M38 52 L50 8" stroke="#8a5a2b" strokeWidth="1.6" strokeLinecap="round" />
      <g fill="#e2a93b" stroke="#b97a18" strokeWidth=".6">
        <path d="M45 26 l4 -3 l3 3 l-1 5 l-5 1 z" />
        <path d="M46 19 l4 -2 l3 3 l-2 4 l-4 0 z" />
        <path d="M48 12 l3 -2 l2 3 l-2 3 l-3 -1 z" />
        <path d="M43 32 l3 -2 l3 3 l-2 3 l-4 -1 z" />
      </g>
      {/* estekan: the tulip-waisted tea glass */}
      <path d="M17 21 C15 32 21 36 20 42 C19 48 22 52 30 52 C38 52 41 48 40 42 C39 36 45 32 43 21 Z"
        fill="#fbf7f0" opacity=".55" stroke="#9aa3ad" strokeWidth="1" />
      {/* tea */}
      <path d="M17.6 27 C17 33 21.5 37 20.6 42.5 C19.8 48 22.5 51 30 51 C37.5 51 40.2 48 39.4 42.5 C38.5 37 43 33 42.4 27 Z"
        fill="#b5481e" />
      <path d="M17.6 27 C17 33 21.5 37 20.6 42.5 L23 42.5 C24 37 20 33 20.5 27 Z" fill="#d8743d" opacity=".7" />
      <ellipse cx="30" cy="27" rx="12.4" ry="1.6" fill="#cf6a2e" />
      {/* rim + gold band */}
      <ellipse cx="30" cy="21" rx="13" ry="1.8" fill="none" stroke="#9aa3ad" strokeWidth="1" />
      <path d="M19.4 44 C24 45.6 36 45.6 40.6 44" stroke="#c99a4a" strokeWidth="1.2" fill="none" />
      {/* steam */}
      <g stroke="#9aa3ad" strokeWidth="1.2" fill="none" strokeLinecap="round" opacity=".7">
        <path d="M26 16 c-2 -3 2 -5 0 -8" />
        <path d="M32 15 c-2 -3 2 -5 0 -8" />
      </g>
    </g>
  )
}

function Anaar() {
  return (
    <g>
      {/* leaf */}
      <path d="M37 13 C44 6 53 8 55 11 C50 15 43 16 37 13 Z" fill="#5f8a3a" />
      <path d="M38 13 C44 11 49 11 54 11" stroke="#46692a" strokeWidth=".8" fill="none" />
      {/* fruit */}
      <circle cx="31" cy="36" r="20" fill="#b3242f" />
      <path d="M14 40 A20 20 0 0 0 48 46 C40 52 22 52 14 40 Z" fill="#8e1a25" opacity=".55" />
      <ellipse cx="23" cy="28" rx="5" ry="3.2" fill="#e05a62" opacity=".55" transform="rotate(-30 23 28)" />
      {/* crown (calyx) */}
      <path d="M25 18 L27 10 L29.5 15 L31 8.5 L32.5 15 L35 10 L37 18 Z" fill="#9b1d27" stroke="#7a1520" strokeWidth=".8" strokeLinejoin="round" />
      <ellipse cx="31" cy="18" rx="6.5" ry="2" fill="#7a1520" />
      {/* a few arils peeking through a crack */}
      <path d="M38 40 C42 38 46 40 46 44 C43 47 39 46 38 40 Z" fill="#6e1019" />
      <g fill="#e8414f">
        <circle cx="41" cy="42" r="1.4" /><circle cx="43.6" cy="42.4" r="1.3" /><circle cx="42.2" cy="44.4" r="1.3" />
      </g>
    </g>
  )
}

function Peste() {
  return (
    <g>
      {/* back nut */}
      <g transform="rotate(-24 22 38)">
        <ellipse cx="22" cy="38" rx="11" ry="15" fill="#e3d2b3" stroke="#b8a17a" strokeWidth="1" />
        <path d="M14 30 C17 37 17 44 15 50" stroke="#c9b48e" strokeWidth="1" fill="none" />
        <ellipse cx="25" cy="37" rx="5.5" ry="10.5" fill="#7fa23d" />
        <ellipse cx="25.6" cy="36" rx="3.4" ry="7.5" fill="#9bbd4f" />
        <path d="M23 31 C26 34 26 40 24 44" stroke="#8a4f6b" strokeWidth="1.2" fill="none" opacity=".6" />
      </g>
      {/* front nut, opened wider */}
      <g transform="rotate(18 42 40)">
        <path d="M33 40 C33 27 38 22 42 22 C46 22 51 27 51 40 C51 50 47 55 42 55 C37 55 33 50 33 40 Z"
          fill="#ead9bb" stroke="#b8a17a" strokeWidth="1" />
        <ellipse cx="42" cy="39" rx="5.8" ry="11" fill="#7fa23d" />
        <ellipse cx="42.6" cy="38" rx="3.6" ry="8" fill="#a7c75a" />
        <path d="M40 32 C43 35 43 42 41 46" stroke="#8a4f6b" strokeWidth="1.2" fill="none" opacity=".6" />
      </g>
    </g>
  )
}
