import type { ReactNode } from 'react'
import { BookText, Check, Flag, Lock, MessageCircle, Play } from 'lucide-react'
import { courseApi, type Course, type LessonState, type UnitSummary } from '../lib/course-api'
import { useAsync } from '../lib/hooks'
import { languageName } from '../lib/rtl'
import { useNav } from '../state/nav'
import { useSettings } from '../state/settings'
import { Button, Empty, ErrorNote, Loading, Page, ProgressLine } from '../components/ui'

export default function PathView() {
  const { pair } = useSettings()
  const nav = useNav()
  const courses = useAsync(`${pair.target}|${pair.support}|${nav.dataVersion}`, () => courseApi.courses(pair.target, pair.support))
  const courseId = courses.data?.[0]?.id ?? null
  const course = useAsync(courseId ? `${courseId}|${nav.dataVersion}` : null, () => courseApi.course(courseId!))

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
      </div>

      <div className="space-y-12">
        {c.units.map((u, i) => <UnitSection key={u.id} course={c} unit={u} index={i} />)}
      </div>
    </Page>
  )
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

function UnitSection({ course, unit, index }: { course: Course; unit: UnitSummary; index: number }) {
  const nav = useNav()
  // The quiz opens as soon as the unit is reached; before its lessons are done it is a test-out.
  const testOut = unit.quiz_state === 'current' && !unit.done

  return (
    <section aria-labelledby={`unit-${unit.id}`}>
      <p className="text-[13px] font-medium uppercase tracking-[0.08em] text-ink-3">Unit {index + 1}</p>
      <h2 id={`unit-${unit.id}`} className="mt-0.5 text-xl font-semibold tracking-tight">{unit.title}</h2>
      {unit.goal && <p className="mt-1 text-sm text-ink-2">{unit.goal}</p>}

      <ol className="mt-5">
        {unit.lessons.map((l) => (
          <Node
            key={l.id}
            state={l.state}
            title={l.title}
            detail={l.state === 'done' && l.best_score !== null ? `Best ${Math.round(l.best_score * 100)}%` : `${l.item_count} items`}
            onClick={() => nav.open({ kind: 'lesson-sheet', courseId: course.id, lessonId: l.id, locked: l.state === 'locked' })}
          />
        ))}
        {unit.story_id && (
          <Node
            state={unit.story_unlocked ? 'open' : 'locked'}
            icon={<BookText size={18} />}
            title="Story"
            detail="Read and listen"
            onClick={unit.story_unlocked ? () => nav.open({ kind: 'story', id: unit.story_id! }) : undefined}
          />
        )}
        {unit.scenario_id && (
          <Node
            state={unit.scenario_unlocked ? 'open' : 'locked'}
            icon={<MessageCircle size={18} />}
            title="Role-play"
            detail="Practise a conversation"
            onClick={unit.scenario_unlocked ? () => nav.open({ kind: 'talk', scenarioId: unit.scenario_id }) : undefined}
          />
        )}
        <Node
          state={testOut ? 'open' : unit.quiz_state}
          icon={<Flag size={18} />}
          title={testOut ? 'Test out' : 'Checkpoint quiz'}
          detail={
            unit.quiz_state === 'locked' ? 'Opens when you reach this unit' :
            unit.quiz_state === 'done' ? 'Passed' :
            testOut ? 'Already know this? Passing marks the unit’s lessons done.' :
            'Pass it to finish the unit.'
          }
          last
          onClick={unit.quiz_state === 'locked' ? undefined : () => nav.open({
            kind: 'player',
            source: { type: 'quiz', courseId: course.id, unitId: unit.id, title: `${unit.title} · checkpoint`, testOut },
          })}
        />
      </ol>
    </section>
  )
}

function Node({ state, title, detail, icon, onClick, last }: {
  state: LessonState | 'open'
  title: string
  detail?: string
  icon?: ReactNode
  onClick?: () => void
  last?: boolean
}) {
  const circle = {
    done: 'bg-accent-soft text-accent',
    current: 'bg-accent text-accent-ink ring-4 ring-accent-soft',
    open: 'border border-line-strong bg-surface text-ink-2',
    locked: 'border border-line bg-surface-2 text-ink-3',
  }[state]
  const glyph =
    state === 'done' && !icon ? <Check size={20} strokeWidth={2.25} /> :
    state === 'current' && !icon ? <Play size={18} fill="currentColor" className="ms-0.5" /> :
    state === 'locked' && !icon ? <Lock size={16} /> :
    icon ?? <Play size={18} />
  const muted = state === 'locked'
  const stateLabel = { done: 'done', current: 'up next', open: 'available', locked: 'locked' }[state]

  return (
    <li className="relative">
      {!last && <span aria-hidden className="absolute start-[23.5px] top-14 h-[calc(100%-3rem)] w-px bg-line-strong" />}
      <button
        type="button"
        onClick={onClick}
        disabled={!onClick}
        aria-label={`${title}, ${stateLabel}`}
        className="flex w-full items-center gap-4 rounded-2xl py-2 pe-2 text-start transition-colors enabled:hover:bg-surface-2/60 disabled:cursor-default"
      >
        <span className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-full ${circle}`}>{glyph}</span>
        <span className="min-w-0 flex-1">
          <span className={`block truncate text-[15px] ${muted ? 'text-ink-3' : state === 'current' ? 'font-medium text-ink' : 'text-ink'}`}>{title}</span>
          {detail && <span className="block text-[13px] text-ink-3">{detail}</span>}
        </span>
      </button>
      {!last && <div className="h-3" />}
    </li>
  )
}
