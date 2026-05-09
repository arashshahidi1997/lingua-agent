import { useEffect, useState } from 'react'
import { api, type Language } from '../lib/api'
import { ErrorBanner, Loading, Section } from '../components/ui'

export default function Languages() {
  const [langs, setLangs] = useState<Language[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.languages().then(setLangs).catch((e) => setError(String(e)))
  }, [])

  return (
    <Section title="Supported languages">
      <ErrorBanner error={error} />
      {!langs && !error && <Loading />}
      {langs && (
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-2">Code</th>
                <th className="px-4 py-2">Name</th>
                <th className="px-4 py-2">Native</th>
                <th className="px-4 py-2">Script</th>
                <th className="px-4 py-2">Direction</th>
                <th className="px-4 py-2">Translit</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {langs.map((lang) => (
                <tr key={lang.code}>
                  <td className="px-4 py-2 font-mono">{lang.code}</td>
                  <td className="px-4 py-2">{lang.name}</td>
                  <td className="px-4 py-2" dir={lang.direction}>{lang.native_name}</td>
                  <td className="px-4 py-2">{lang.script}</td>
                  <td className="px-4 py-2">{lang.direction}</td>
                  <td className="px-4 py-2">{lang.transliteration_supported ? 'yes' : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Section>
  )
}
