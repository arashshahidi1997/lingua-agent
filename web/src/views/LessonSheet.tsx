import { courseApi } from '../lib/course-api'
import { useAsync } from '../lib/hooks'
import { Markdown } from '../lib/markdown'
import { dirOf } from '../lib/rtl'
import { useNav } from '../state/nav'
import { useSettings } from '../state/settings'
import { Button, ErrorNote, Loading, Sheet } from '../components/ui'
import { ItemText } from '../components/Text'
import { PlayButton } from '../components/PlayButton'

export default function LessonSheet({ courseId, lessonId, locked }: { courseId: string; lessonId: string; locked: boolean }) {
  const nav = useNav()
  const { pair, settings } = useSettings()
  // Fast track opens every lesson and runs it as a quiz.
  const fast = settings.fastTrack
  locked = locked && !fast
  const { data, error, reload } = useAsync(`${courseId}/${lessonId}`, () => courseApi.lesson(courseId, lessonId))

  const start = () => nav.replace({
    kind: 'player',
    source: { type: 'lesson', courseId, lessonId, title: data?.title, fast },
  })

  return (
    <Sheet
      onClose={nav.close}
      label={data?.title ?? 'Lesson'}
      footer={
        <div className="flex items-center gap-3">
          {locked && <p className="min-w-0 flex-1 text-[13px] text-ink-3">Finish the lessons before this one to unlock it.</p>}
          {fast && <p className="min-w-0 flex-1 text-[13px] text-ink-3">Fast track: straight to the questions.</p>}
          <Button size="lg" block={!locked && !fast} disabled={locked || !data} onClick={start}>
            Start
          </Button>
        </div>
      }
    >
      {!data && !error && <Loading />}
      <ErrorNote error={error} onRetry={reload} />
      {data && (
        <div>
          <p className="text-[13px] uppercase tracking-[0.08em] text-ink-3">{data.kind}</p>
          <h2 className="mt-0.5 text-[1.4rem] font-semibold tracking-tight">{data.title}</h2>
          {data.note && <Markdown text={data.note} rtlLang={dirOf(pair.target) === 'rtl' ? pair.target : 'fa'} className="mt-3 text-[15px] leading-relaxed text-ink-2" />}

          <ul className="mt-6 divide-y divide-line border-t border-line">
            {data.items.map((it) => (
              <li key={it.id} className="flex items-center gap-3 py-3">
                <div className="min-w-0 flex-1">
                  <ItemText text={it.text} tr={it.tr} gloss={it.gloss} lang={pair.target} supportLang={pair.support} size="sm" glossMode="show" />
                </div>
                <PlayButton text={it.text} lang={pair.target} size="sm" />
              </li>
            ))}
          </ul>
        </div>
      )}
    </Sheet>
  )
}
