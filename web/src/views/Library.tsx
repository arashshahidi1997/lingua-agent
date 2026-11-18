import { BookText, Check, FileText, Lightbulb, Lock, MessagesSquare, Plus } from 'lucide-react'
import { api } from '../lib/api'
import { courseApi } from '../lib/course-api'
import { useAsync } from '../lib/hooks'
import { useIngestJob } from '../lib/pending-ingest'
import { languageName } from '../lib/rtl'
import { useNav, type LibrarySection } from '../state/nav'
import { useSettings } from '../state/settings'
import { Button, Empty, ErrorNote, List, Loading, Page, PageTitle, Row, Segmented, Spinner } from '../components/ui'
import { Target } from '../components/Text'
import AudioSection from './AudioSection'
import AddText from './AddText'

const SECTIONS: { value: Exclude<LibrarySection, 'add'>; label: string }[] = [
  { value: 'stories', label: 'Stories' },
  { value: 'grammar', label: 'Grammar' },
  { value: 'audio', label: 'Audio' },
  { value: 'lessons', label: 'Your lessons' },
]

export default function Library() {
  const nav = useNav()
  const section = nav.librarySection

  return (
    <Page>
      <PageTitle
        title="Library"
        action={
          section !== 'add' && (
            <Button size="sm" variant="secondary" onClick={() => nav.setLibrarySection('add')}>
              <Plus size={16} aria-hidden /> Add
            </Button>
          )
        }
      />
      {section !== 'add' && (
        <div className="mb-6">
          <Segmented label="Library section" value={section} options={SECTIONS} onChange={nav.setLibrarySection} />
        </div>
      )}
      {section === 'stories' && <Stories />}
      {section === 'grammar' && <Grammar />}
      {section === 'audio' && <AudioSection />}
      {section === 'lessons' && <YourLessons />}
      {section === 'add' && <AddText onBack={() => nav.setLibrarySection('lessons')} />}
    </Page>
  )
}

function Grammar() {
  const { pair } = useSettings()
  const nav = useNav()
  const courses = useAsync(`courses|${pair.target}|${pair.support}`, () => courseApi.courses(pair.target, pair.support))
  const courseId = courses.data?.[0]?.id ?? null
  const topics = useAsync(courseId ? `grammar|${courseId}|${nav.dataVersion}` : null, () => courseApi.grammarTopics(courseId!))

  if (courses.data && !courseId) return <Empty title="No grammar lab yet">The grammar lab comes with a course for {languageName(pair.target)}.</Empty>
  if (topics.error?.startsWith('404')) return <Empty title="No grammar lab yet">This course has no grammar topics yet.</Empty>
  if (topics.error) return <ErrorNote error={topics.error} onRetry={topics.reload} />
  if (!topics.data) return <Loading />
  if (topics.data.length === 0) return <Empty title="Grammar topics are coming">They are being reviewed and appear here soon.</Empty>
  return (
    <>
      <p className="mb-4 text-[15px] text-ink-2">
        Find the pattern yourself from examples, then check it against the rule and try it out. Rule cards stay here.
      </p>
      <List>
        {topics.data.map((t) => (
          <Row
            key={t.id}
            icon={t.done ? <Check size={18} /> : <Lightbulb size={18} />}
            title={<span>{t.title} {t.title_fa && <span className="text-ink-3">· <Target text={t.title_fa} lang={pair.target} /></span>}</span>}
            detail={`${t.status === 'draft' ? 'Draft for your review · ' : ''}${t.task_count} tasks${t.best_score !== null ? ` · best ${Math.round(t.best_score * 100)}%` : ''}`}
            onClick={() => nav.open({ kind: 'grammar', courseId: courseId!, topicId: t.id })}
          />
        ))}
      </List>
    </>
  )
}

function Stories() {
  const { pair } = useSettings()
  const nav = useNav()
  const { data, error, loading, reload } = useAsync(`stories|${pair.target}|${pair.support}|${nav.dataVersion}`,
    () => courseApi.stories(pair.target, pair.support))

  if (loading && !data) return <Loading />
  if (error && !data) {
    if (error.startsWith('404')) return <Empty title="No stories yet">Stories come with a course. They appear here as you work through the Path.</Empty>
    return <ErrorNote error={error} onRetry={reload} />
  }
  if (!data?.length) {
    return <Empty title="No stories yet">Stories come with a course for {languageName(pair.target)}. They appear here as you work through the Path.</Empty>
  }
  return (
    <List>
      {data.map((s) => (
        <Row
          key={s.id}
          icon={s.unlocked ? (s.kind === 'dialogue' ? <MessagesSquare size={18} /> : <BookText size={18} />) : <Lock size={16} />}
          title={<span className={s.unlocked ? '' : 'text-ink-3'}><Target text={s.title} lang={pair.target} /></span>}
          detail={`${s.title_gloss} · ${s.kind} · ${s.line_count} lines${s.unlocked ? '' : ' · locked'}`}
          onClick={s.unlocked ? () => nav.open({ kind: 'story', id: s.id }) : undefined}
          trailing={s.unlocked ? undefined : <span />}
        />
      ))}
    </List>
  )
}

function YourLessons() {
  const { pair } = useSettings()
  const nav = useNav()
  const { data, error, loading, reload } = useAsync(`units|${pair.target}|${nav.dataVersion}`, () => api.units(pair.target))
  const job = useIngestJob()
  const making = job && !job.done ? (
    <button type="button" onClick={() => nav.setLibrarySection('add')} className="mb-4 flex w-full items-center justify-between gap-3 rounded-xl bg-surface-2 px-4 py-3 text-start text-sm text-ink">
      <span className="min-w-0 truncate">“{job.title}” is still being made</span>
      <Spinner label="Working" />
    </button>
  ) : null

  if (loading && !data) return <>{making}<Loading /></>
  if (error && !data) return <ErrorNote error={error} onRetry={reload} />
  if (!data?.length) {
    return (
      <>
      {making}
      <Empty
        title="No lessons of your own yet"
        action={<Button variant="secondary" onClick={() => nav.setLibrarySection('add')}><Plus size={16} aria-hidden /> Add a text</Button>}
      >
        Paste any {languageName(pair.target)} text and it becomes a lesson with vocabulary, grammar notes and cards.
      </Empty>
      </>
    )
  }
  return (
    <>
    {making}
    <List>
      {data.map((u) => (
        <Row
          key={u.id}
          icon={<FileText size={18} />}
          title={u.title}
          detail={[u.cefr_level, `${u.vocabulary_count} words`, `${u.flashcard_count} cards`, new Date(u.created_at).toLocaleDateString()].filter(Boolean).join(' · ')}
          onClick={() => nav.open({ kind: 'unit', id: u.id })}
        />
      ))}
    </List>
    </>
  )
}
