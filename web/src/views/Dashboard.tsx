import { useEffect, useState } from 'react'
import { api, type Health } from '../lib/api'
import { Card, ErrorBanner, Loading, Section } from '../components/ui'

export default function Dashboard() {
  const [health, setHealth] = useState<Health | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.health().then(setHealth).catch((e) => setError(String(e)))
  }, [])

  return (
    <Section title="Dashboard">
      <ErrorBanner error={error} />
      <Card title="Backend">
        {!health && !error && <Loading label="Pinging backend…" />}
        {health && (
          <ul className="space-y-1 text-sm">
            <li><span className="text-slate-500">status:</span> <span className="font-medium">{health.status}</span></li>
            <li><span className="text-slate-500">version:</span> <span className="font-medium">{health.version}</span></li>
            <li><span className="text-slate-500">AI provider:</span> <span className="font-medium">{health.ai_provider}</span></li>
          </ul>
        )}
      </Card>
      <Card title="What works here">
        <ul className="list-inside list-disc space-y-1 text-sm text-slate-700">
          <li><strong>Ingest</strong> — paste text → lesson + vocab + grammar + cards.</li>
          <li><strong>Lessons</strong> — bilingual reader with RTL handling for Persian.</li>
          <li><strong>Review</strong> — SM-2 SRS with reveal + 0–5 quality buttons.</li>
          <li><strong>Tutor</strong> — chat against the configured AI provider.</li>
          <li><strong>Install to home screen</strong> — this is a PWA. On Android Chrome and iOS Safari, the browser menu has an "Install" / "Add to Home Screen" option. Offline access works for previously-loaded pages and cached API responses (network-first with 14-day cache).</li>
        </ul>
      </Card>
    </Section>
  )
}
