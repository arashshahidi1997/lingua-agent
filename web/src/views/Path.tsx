import { useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import { BookText, Check, Flag, Lock, MessageCircle, Play, Lightbulb } from 'lucide-react'
import { courseApi, type Course, type GrammarTopicSummary, type LessonState, type UnitSummary } from '../lib/course-api'
import { useAsync } from '../lib/hooks'
import { languageName } from '../lib/rtl'
import { useNav } from '../state/nav'
import { useSettings } from '../state/settings'
import { Button, Empty, ErrorNote, Loading, Page, ProgressLine, Toggle } from '../components/ui'
import { Target } from '../components/Text'
import { Treat } from '../components/Treats'
import { TREATS, treatFor } from '../lib/treats'

export default function PathView() {
  const { pair, settings, update } = useSettings()
  const nav = useNav()
  const courses = useAsync(`${pair.target}|${pair.support}|${nav.dataVersion}`, () => courseApi.courses(pair.target, pair.support))
  const courseId = courses.data?.[0]?.id ?? null
  const course = useAsync(courseId ? `${courseId}|${nav.dataVersion}` : null, () => courseApi.course(courseId!))
  // Grammar topics belong to a unit; 404 (no grammar lab for this course) just means none.
  const grammar = useAsync(courseId ? `grammar|${courseId}|${nav.dataVersion}` : null, () => courseApi.grammarTopics(courseId!).catch(() => []))

  if (courses.error && !courses.data) {
    if (courses.error.startsWith('404')) return <Page><NoCourse /></Page>
    return <Page><ErrorNote error={courses.error} onRetry={courses.reload} /></Page>
  }
  if (courses.data && courses.data.length === 0) return <Page><NoCourse /></Page>
  if (course.error && !course.data) return <Page><ErrorNote error={course.error} onRetry={course.reload} /></Page>
  if (!course.data) return <Page><Loading /></Page>

  const c = course.data
  return (
    <Page>
      <div className="mb-10 pt-4">
        <p className="text-[13px] uppercase tracking-[0.08em] text-ink-3">{c.level} · {languageName(c.target)}</p>
        <h1 className="mt-1 text-[1.75rem] font-semibold leading-tight tracking-tight">{c.title}</h1>
        {c.description && <p className="mt-2 text-[15px] text-ink-2">{c.description}</p>}
        <div className="mt-5 flex items-center gap-3">
          <ProgressLine value={c.progress} label="Course progress" />
          <span className="shrink-0 text-[13px] tabular-nums text-ink-3">{c.lessons_done}/{c.lessons_total}</span>
        </div>
        <div className="mt-4 max-w-md">
          <Toggle
            label="Fast track"
            description="Every lesson open, straight to the questions: no introductions, no transliteration help."
            checked={settings.fastTrack}
            onChange={(v) => update({ fastTrack: v })}
          />
        </div>
      </div>

      <div className="space-y-6">
        {c.units.map((u, i) => (
          <UnitSection key={u.id} course={c} unit={u} index={i} startStep={stepsBefore(c, i, grammar.data ?? [])}
            grammar={(grammar.data ?? []).filter((g) => g.unit === u.id)} />
        ))}
      </div>
    </Page>
  )
}

/** Steps on the road before unit i (lessons, story, role-play, quiz and the milestone), so the wave flows on. */
function stepsBefore(c: Course, i: number, grammar: GrammarTopicSummary[]): number {
  return c.units.slice(0, i).reduce((n, u) => n + u.lessons.length + (u.story_id ? 1 : 0) + (u.scenario_id ? 1 : 0) + 2
    + grammar.filter((g) => g.unit === u.id).length, 0)
}

function NoCourse() {
  const { pair } = useSettings()
  const nav = useNav()
  return (
    <div className="pt-6">
      <Empty
        title={`No course for ${languageName(pair.target)} yet`}
        action={<Button variant="secondary" onClick={() => { nav.setLibrarySection('add'); nav.setTab('library') }}>Add your own text</Button>}
      >
        There’s no ready-made course for this language yet. Meanwhile, any text you add in Library becomes a lesson.
      </Empty>
    </div>
  )
}

// ---- the winding path ------------------------------------------------------------------

const ROW = 112          // vertical distance between steps
const NODE = 56          // step circle
const STEP_ANGLE = Math.PI / 2.6

interface Step {
  key: string
  state: LessonState | 'open'
  title: string
  detail?: string
  icon?: ReactNode
  onClick?: () => void
}

/** Width of an element, kept current. */
function useWidth<T extends HTMLElement>(): [React.RefObject<T | null>, number] {
  const ref = useRef<T>(null)
  const [w, setW] = useState(340)
  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    const update = () => setW(el.clientWidth)
    update()
    const ro = new ResizeObserver(update)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  return [ref, w]
}

function UnitSection({ course, unit, index, startStep, grammar }: {
  course: Course; unit: UnitSummary; index: number; startStep: number; grammar: GrammarTopicSummary[]
}) {
  const nav = useNav()
  const { settings } = useSettings()
  const fast = settings.fastTrack
  const [ref, width] = useWidth<HTMLDivElement>()
  // The quiz opens as soon as the unit is reached; before its lessons are done it is a test-out.
  const testOut = unit.quiz_state === 'current' && !unit.done

  const steps: Step[] = [
    ...unit.lessons.map((l): Step => ({
      key: l.id,
      state: fast && l.state === 'locked' ? 'open' : l.state,
      title: l.title,
      detail: l.state === 'done' && l.best_score !== null ? `Best ${Math.round(l.best_score * 100)}%` : `${l.item_count} items`,
      onClick: () => nav.open({ kind: 'lesson-sheet', courseId: course.id, lessonId: l.id, locked: l.state === 'locked' && !fast }),
    })),
    // Grammar lab topics of this unit: open once the unit is reached.
    ...grammar.map((g): Step => ({
      key: `grammar-${g.id}`,
      state: g.done ? 'done' : unit.story_unlocked || fast ? 'open' : 'locked',
      icon: g.done ? undefined : <Lightbulb size={20} />,
      title: g.title,
      detail: g.done ? 'Grammar · rule card' : 'Grammar · find the pattern',
      onClick: unit.story_unlocked || fast || g.done ? () => nav.open({ kind: 'grammar', courseId: course.id, topicId: g.id }) : undefined,
    })),
    ...(unit.story_id ? [{
      key: 'story',
      state: unit.story_unlocked ? 'open' : 'locked',
      icon: <BookText size={20} />,
      title: 'Story',
      detail: 'Read and listen',
      onClick: unit.story_unlocked ? () => nav.open({ kind: 'story', id: unit.story_id! }) : undefined,
    } as Step] : []),
    ...(unit.scenario_id ? [{
      key: 'role-play',
      state: unit.scenario_unlocked ? 'open' : 'locked',
      icon: <MessageCircle size={20} />,
      title: 'Role-play',
      detail: 'Practise a conversation',
      onClick: unit.scenario_unlocked ? () => nav.open({ kind: 'talk', scenarioId: unit.scenario_id }) : undefined,
    } as Step] : []),
    {
      key: 'quiz',
      state: testOut ? 'open' : unit.quiz_state,
      icon: <Flag size={20} />,
      title: testOut ? 'Test out' : 'Checkpoint quiz',
      detail:
        unit.quiz_state === 'locked' ? 'Opens when you reach this unit' :
        unit.quiz_state === 'done' ? 'Passed' :
        testOut ? 'Already know it? Passing marks the lessons done.' :
        'Pass it to finish the unit.',
      onClick: unit.quiz_state === 'locked' ? undefined : () => nav.open({
        kind: 'player',
        source: { type: 'quiz', courseId: course.id, unitId: unit.id, title: `${unit.title} · checkpoint`, testOut },
      }),
    },
  ]

  // Positions: a gentle wave across the column, continuing from the previous unit so the road flows on.
  const amp = Math.max(0, Math.min(width / 2 - 92, 120))
  const xAt = (i: number) => width / 2 + amp * Math.sin((startStep + i) * STEP_ANGLE)
  const points = steps.map((_, i) => ({ x: xAt(i), y: NODE / 2 + i * ROW }))
  const milestone = { x: xAt(steps.length), y: NODE / 2 + steps.length * ROW + 8 }
  const height = milestone.y + 96

  // The road is solid as far as the learner has come, dotted beyond.
  const reached = steps.reduce((acc, st, i) => (st.state === 'done' || st.state === 'current' ? i : acc), -1)
  const earned = unit.done || unit.quiz_state === 'done'
  const all = [...points, milestone]
  const seg = (a: { x: number; y: number }, b: { x: number; y: number }) =>
    `M${a.x} ${a.y} C${a.x} ${a.y + ROW * 0.55} ${b.x} ${b.y - ROW * 0.55} ${b.x} ${b.y}`
  const kind = treatFor(index)
  const treat = TREATS[kind]

  return (
    <section aria-labelledby={`unit-${unit.id}`}>
      <p className="text-[13px] font-medium uppercase tracking-[0.08em] text-ink-3">Unit {index + 1}</p>
      <h2 id={`unit-${unit.id}`} className="mt-0.5 text-xl font-semibold tracking-tight">{unit.title}</h2>
      {unit.goal && <p className="mt-1 text-sm text-ink-2">{unit.goal}</p>}

      <div ref={ref} className="relative mt-6" style={{ height }}>
        <svg className="pointer-events-none absolute inset-0" width={width} height={height} aria-hidden="true">
          {all.slice(1).map((b, i) => {
            const done = i < reached || (i === all.length - 2 && earned)
            return (
              <path
                key={i}
                d={seg(all[i], b)}
                fill="none"
                strokeLinecap="round"
                style={{ stroke: done ? 'var(--accent)' : 'var(--line-strong, #c9c3b8)' }}
                strokeWidth={done ? 6 : 3}
                strokeDasharray={done ? undefined : '1 9'}
                opacity={done ? 0.45 : 1}
              />
            )
          })}
        </svg>

        <ol className="absolute inset-0">
          {steps.map((st, i) => (
            <PathNode key={st.key} step={st} x={points[i].x} y={points[i].y} />
          ))}
        </ol>

        <figure
          className="absolute flex w-40 -translate-x-1/2 flex-col items-center text-center"
          style={{ left: milestone.x, top: milestone.y - 34 }}
          role="img"
          aria-label={`Unit ${index + 1} milestone: ${treat.gloss}${earned ? ', reached' : ', not reached yet'}`}
        >
          <Treat kind={kind} earned={earned} size={68} />
          <figcaption className={`mt-0.5 rounded-lg bg-canvas/90 px-2 py-0.5 leading-tight ${earned ? 'text-ink' : 'text-ink-3'}`}>
            <Target text={treat.fa} tr={treat.tr} lang="fa" stack className="text-[15px]" />
            <span className="block text-[12px] text-ink-3">{earned ? treat.gloss : `${treat.gloss} · after this unit`}</span>
          </figcaption>
        </figure>
      </div>
    </section>
  )
}

function PathNode({ step, x, y }: { step: Step; x: number; y: number }) {
  const { state, title, detail, icon, onClick } = step
  const circle = {
    done: 'bg-accent-soft text-accent',
    current: 'bg-accent text-accent-ink ring-[6px] ring-accent-soft',
    open: 'border-2 border-line-strong bg-surface text-ink-2',
    locked: 'border border-line bg-surface-2 text-ink-3',
  }[state]
  const glyph =
    state === 'done' && !icon ? <Check size={22} strokeWidth={2.25} /> :
    state === 'current' && !icon ? <Play size={20} fill="currentColor" className="ms-0.5" /> :
    state === 'locked' && !icon ? <Lock size={18} /> :
    icon ?? <Play size={20} />
  const muted = state === 'locked'
  const stateLabel = { done: 'done', current: 'up next', open: 'available', locked: 'locked' }[state]

  return (
    <li className="absolute w-44 -translate-x-1/2" style={{ left: x, top: y - NODE / 2 }}>
      <button
        type="button"
        onClick={onClick}
        disabled={!onClick}
        aria-label={`${title}, ${stateLabel}`}
        className="group flex w-full flex-col items-center gap-1.5 rounded-2xl text-center disabled:cursor-default"
      >
        <span
          className={`flex shrink-0 items-center justify-center rounded-full transition-transform group-enabled:group-hover:scale-105 ${circle}`}
          style={{ width: NODE, height: NODE }}
        >
          {glyph}
        </span>
        <span className="block max-w-full rounded-lg bg-canvas/90 px-2 py-0.5">
          <span className={`block truncate text-[14px] leading-tight ${muted ? 'text-ink-3' : state === 'current' ? 'font-medium text-ink' : 'text-ink'}`}>{title}</span>
          {detail && <span className="mt-0.5 line-clamp-2 block text-[12px] leading-snug text-ink-3">{detail}</span>}
        </span>
      </button>
    </li>
  )
}
