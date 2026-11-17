import { Lock, MessageCircle, MessagesSquare } from 'lucide-react'
import { courseApi } from '../lib/course-api'
import { useAsync } from '../lib/hooks'
import { languageName } from '../lib/rtl'
import { useNav } from '../state/nav'
import { useTalkEnabled } from '../lib/features'
import { useSettings } from '../state/settings'
import { ErrorNote, List, Loading, Page, PageTitle, Row, SectionLabel } from '../components/ui'
import { Target } from '../components/Text'

export default function Talk() {
  const { pair } = useSettings()
  const nav = useNav()
  const talkOn = useTalkEnabled()
  const { data, error, loading, reload } = useAsync(`scenarios|${pair.target}|${pair.support}|${nav.dataVersion}`,
    () => courseApi.scenarios(pair.target, pair.support))

  return (
    <Page>
      <PageTitle
        title="Talk"
        subtitle={talkOn === false
          ? `Role-plays to practise ${languageName(pair.target)} with the AI chatbot you use, typing or by voice. Pick one, copy its prompt, and start.`
          : `Practise ${languageName(pair.target)} in conversation. Mistakes are fine; you’ll get gentle corrections.`}
      />

      {talkOn && (
        <List>
          <Row
            icon={<MessagesSquare size={18} />}
            title="Free conversation"
            detail="Talk about anything, at your level"
            onClick={() => nav.open({ kind: 'talk', scenarioId: null })}
          />
        </List>
      )}

      <SectionLabel className={talkOn ? 'mt-10' : 'mt-2'}>Role-play</SectionLabel>
      {loading && !data && <Loading />}
      {error && !data && !error.startsWith('404') && <ErrorNote error={error} onRetry={reload} />}
      {(data?.length === 0 || error?.startsWith('404')) && (
        <p className="py-2 text-sm text-ink-3">Role-plays come with a course and unlock as you go.</p>
      )}
      {data && data.length > 0 && (
        <List>
          {data.map((s) => (
            <Row
              key={s.id}
              icon={s.unlocked ? <MessageCircle size={18} /> : <Lock size={16} />}
              title={
                <span className={s.unlocked ? '' : 'text-ink-3'}>
                  {s.title} <span className="text-ink-3">· <Target text={s.title_target} lang={pair.target} /></span>
                </span>
              }
              detail={s.unlocked ? s.goal : `Locked · ${s.goal}`}
              onClick={s.unlocked ? () => nav.open({ kind: 'talk', scenarioId: s.id }) : undefined}
            />
          ))}
        </List>
      )}
    </Page>
  )
}
