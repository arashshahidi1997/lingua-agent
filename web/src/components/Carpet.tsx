// Persian-carpet border, purely decorative. One 48 × 72 tile that repeats down the page without seams:
// a madder-red main band with diamond medallions and small saffron rosettes, framed by ivory minor guards
// with little red diamonds and thin indigo stripes. Colours are the --carpet-* tokens in index.css (light
// and dark); the whole thing is drawn at --carpet-opacity so it stays behind the lesson.

import { useId } from 'react'

function Tile() {
  // Medallion centres at y = 18 and 54; rosettes at the tile seams (0, 36, 72), drawn on both edges so
  // the halves meet when the tile repeats.
  const medallion = (y: number) => (
    <g key={`m${y}`}>
      <path className="cp-iv" d={`M24 ${y - 15}L35 ${y}L24 ${y + 15}L13 ${y}Z`} />
      <path className="cp-in" d={`M24 ${y - 11}L31.5 ${y}L24 ${y + 11}L16.5 ${y}Z`} />
      <path className="cp-rd" d={`M24 ${y - 6}L28 ${y}L24 ${y + 6}L20 ${y}Z`} />
      <circle className="cp-sf" cx="24" cy={y} r="1.8" />
      <circle className="cp-iv" cx="14.5" cy={y} r="0.9" />
      <circle className="cp-iv" cx="33.5" cy={y} r="0.9" />
    </g>
  )
  const rosette = (y: number) => (
    <g key={`r${y}`}>
      <circle className="cp-iv" cx="24" cy={y - 3} r="1.4" />
      <circle className="cp-iv" cx="24" cy={y + 3} r="1.4" />
      <circle className="cp-iv" cx="21" cy={y} r="1.4" />
      <circle className="cp-iv" cx="27" cy={y} r="1.4" />
      <circle className="cp-sf" cx="24" cy={y} r="1.5" />
    </g>
  )
  const guard = (x: number) =>
    [6, 18, 30, 42, 54, 66].map((y) => (
      <g key={`g${x}-${y}`}>
        <path className="cp-rd" d={`M${x} ${y - 4}L${x + 2.6} ${y}L${x} ${y + 4}L${x - 2.6} ${y}Z`} />
        <circle className="cp-sf" cx={x} cy={y} r="0.8" />
      </g>
    ))
  return (
    <>
      <rect className="cp-iv" width="48" height="72" />
      <rect className="cp-in" x="1" width="1.5" height="72" />
      <rect className="cp-in" x="45.5" width="1.5" height="72" />
      {guard(6.75)}
      {guard(41.25)}
      <rect className="cp-in" x="10.5" width="1" height="72" />
      <rect className="cp-in" x="36.5" width="1" height="72" />
      <rect className="cp-rd" x="11.5" width="25" height="72" />
      <rect className="cp-sf" x="12.5" width="0.5" height="72" />
      <rect className="cp-sf" x="35" width="0.5" height="72" />
      {medallion(18)}
      {medallion(54)}
      {[0, 36, 72].map(rosette)}
    </>
  )
}

function Band({ id, horizontal = false }: { id: string; horizontal?: boolean }) {
  return (
    <svg aria-hidden focusable="false" className="carpet block h-full w-full" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <pattern
          id={id}
          width="48"
          height="72"
          patternUnits="userSpaceOnUse"
          // The phone band lies the border on its side, small.
          patternTransform={horizontal ? 'rotate(-90) scale(0.25)' : undefined}
        >
          <Tile />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill={`url(#${id})`} />
    </svg>
  )
}

/** Two vertical borders in the page margins, on wide screens only (beside the content, clear of the rail). */
export function CarpetMargins() {
  const id = useId().replace(/:/g, '')
  return (
    <div aria-hidden className="carpet-margins pointer-events-none hidden lg:block">
      <div className="carpet-side carpet-start"><Band id={`cm-s-${id}`} /></div>
      <div className="carpet-side carpet-end"><Band id={`cm-e-${id}`} /></div>
    </div>
  )
}

/** A slim band for the top of Today on phones and tablets. */
export function CarpetBand({ className = '' }: { className?: string }) {
  const id = useId().replace(/:/g, '')
  return (
    <div aria-hidden className={`carpet-band pointer-events-none h-3 overflow-hidden rounded-sm ${className}`}>
      <Band id={`cb-${id}`} horizontal />
    </div>
  )
}
