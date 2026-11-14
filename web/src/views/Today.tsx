import { BookText, Layers, MessageCircle, Play, Plus, Sparkles } from 'lucide-react'
import { courseApi } from '../lib/course-api'
import { useAsync } from '../lib/hooks'
import { languageName } from '../lib/rtl'
import { useNav } from '../state/nav'
import { useSettings } from '../state/settings'
import { Button, Empty, ErrorNote, List, Loading, Page, ProgressLine, Row } from '../components/ui'
import { Tgt } from '../components/Text'

function greeting(d: Date): string {
  const h = d.getHours()
  if (h < 5) return 'Good evening'
  if (h < 12) return 'Good morning'
  if (h < 18) return 'Good afternoon'
  return 'Good evening'
}

export default function Today() {
  const { pair, settings } = useSettings()
  const nav = useNav()
  const { data, error, loading, reload } = useAsync(
    `${pair.target}|${pair.support}|${nav.dataVersion}`,
    () => courseApi.today(pair.target, pair.support),
  )

  const now = new Date()
  const day = now.toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long' })

  return (
    <Page>
      <div className="mb-8 pt-4">
        <p className="text-sm text-ink-3">{day}</p>
        <h1 className="mt-1 text-[1.75rem] font-semibold tracking-tight">{greeting(now)}</h1>
      </div>

      {loading && !data && <Loading />}
      {error && !data && (
        error.startsWith('404') ? <NoCourse /> : <ErrorNote error={error} onRetry={reload} />
      )}

      {data && !data.course && <NoCourse />}

      {data?.course && (
        <div className="space-y-8">
          {data.next_lesson ? (
            <button
              type="button"
              onClick={() => nav.open({
                kind: 'player',
                source: { type: 'lesson', courseId: data.course!.id, lessonId: data.next_lesson!.lesson_id, title: data.next_lesson!.title },
              })}
              className="group flex w-full items-center gap-4 rounded-3xl bg-accent p-5 text-start text-accent-ink transition-colors hover:bg-accent-strong sm:p-6"
            >
              <span className="min-w-0 flex-1">
                <span className="block text-[13px] opacity-80">Continue · {data.next_lesson.unit_title}</span>
                <span className="mt-1 block text-xl font-semibold leading-snug">{data.next_lesson.title}</span>
                <span className="mt-2 block text-[13px] opacity-80">{data.course.title}</span>
              </span>
              <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-accent-ink/15">
                <Play size={22} fill="currentColor" className="ms-0.5" aria-hidden />
              </span>
            </button>
          ) : (
            <div className="rounded-3xl border border-line bg-surface p-6">
              <p className="text-[13px] text-ink-3">{data.course.title}</p>
              <p className="mt-1 text-lg font-medium">You’ve finished every lesson in this course.</p>
              <p className="mt-1 text-sm text-ink-2">A quick quiz keeps it fresh.</p>
              <Button className="mt-4" onClick={() => nav.open({ kind: 'player', source: { type: 'practice', courseId: data.course!.id } })}>
                Start a quiz
              </Button>
            </div>
          )}

          <div>
            <div className="mb-2 flex items-baseline justify-between text-[13px] text-ink-3">
              <span>Daily goal</span>
              <span>
                {Math.min(Math.round(data.minutes_today), settings.dailyGoal)} of {settings.dailyGoal} min
                {settings.showStreak && data.streak_days > 0 && (
                  <> · {data.streak_days} day{data.streak_days === 1 ? '' : 's'} in a row</>
                )}
              </span>
            </div>
            <ProgressLine value={data.minutes_today / settings.dailyGoal} label="Daily goal" />
          </div>

          <List>
            <Row
              icon={<Layers size={18} />}
              title={data.due_count > 0 ? `${data.due_count} word${data.due_count === 1 ? '' : 's'} to review` : 'No words due'}
              detail={data.due_count > 0 ? 'Flashcards, a few minutes' : `${data.learned_count} learned so far`}
              onClick={() => nav.open({ kind: 'review' })}
            />
            <Row
              icon={<Sparkles size={18} />}
              title="Quick quiz"
              detail="Mixed practice from what you’ve learned"
              onClick={() => nav.open({ kind: 'player', source: { type: 'practice', courseId: data.course!.id } })}
              disabled={data.learned_count === 0}
            />
            {data.story && (
              <Row
                icon={<BookText size={18} />}
                title={<>Story · <Tgt lang={pair.target}>{data.story.title}</Tgt></>}
                detail={data.story.title_gloss}
                onClick={() => nav.open({ kind: 'story', id: data.story!.id })}
              />
            )}
            {data.scenario && (
              <Row
                icon={<MessageCircle size={18} />}
                title={`Talk · ${data.scenario.title}`}
                detail={data.scenario.goal}
                onClick={() => nav.open({ kind: 'talk', scenarioId: data.scenario!.id })}
              />
            )}
          </List>
        </div>
      )}
    </Page>
  )
}

function NoCourse() {
  const { pair } = useSettings()
  const nav = useNav()
  return (
    <Empty
      title={`There’s no course for ${languageName(pair.source)} → ${languageName(pair.target)} yet`}
      action={
        <Button variant="secondary" onClick={() => { nav.setLibrarySection('add'); nav.setTab('library') }}>
          <Plus size={18} aria-hidden /> Add your own text
        </Button>
      }
    >
      You can still learn from your own material: paste a text in Library and it becomes a lesson.
    </Empty>
  )
}
