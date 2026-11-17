import { BookText, FileText, Lock, MessagesSquare, Plus } from 'lucide-react'
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
      {section === 'audio' && <AudioSection />}
      {section === 'lessons' && <YourLessons />}
      {section === 'add' && <AddText onBack={() => nav.setLibrarySection('lessons')} />}
    </Page>
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
