import { useEffect, useState } from 'react'
import { api, type Language } from '../lib/api'
import { useLangPair } from '../state/LangPair'

export default function PairPicker() {
  const { pair, setPair } = useLangPair()
  const [langs, setLangs] = useState<Language[] | null>(null)

  useEffect(() => { api.languages().then(setLangs).catch(() => setLangs([])) }, [])

  const opts = langs ?? []

  return (
    <div className="space-y-2 text-xs">
      <div>
        <label className="block text-slate-500">Source</label>
        <select
          className="mt-1 block w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
          value={pair.source}
          onChange={(e) => setPair({ ...pair, source: e.target.value })}
        >
          {opts.map((l) => (<option key={l.code} value={l.code}>{l.code} — {l.name}</option>))}
        </select>
      </div>
      <div>
        <label className="block text-slate-500">Target</label>
        <select
          className="mt-1 block w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
          value={pair.target}
          onChange={(e) => setPair({ ...pair, target: e.target.value })}
        >
          {opts.map((l) => (<option key={l.code} value={l.code}>{l.code} — {l.name}</option>))}
        </select>
      </div>
      <div>
        <label className="block text-slate-500">Support</label>
        <select
          className="mt-1 block w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
          value={pair.support ?? ''}
          onChange={(e) => setPair({ ...pair, support: e.target.value || null })}
        >
          <option value="">— none —</option>
          {opts.map((l) => (<option key={l.code} value={l.code}>{l.code} — {l.name}</option>))}
        </select>
      </div>
      {pair.source === pair.target && (
        <p className="text-rose-700">source and target must differ</p>
      )}
    </div>
  )
}
