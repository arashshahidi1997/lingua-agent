// Tiny typed fetch wrapper around the FastAPI backend.
// Every endpoint returns JSON; on non-2xx we throw with the response body
// so the UI can show the backend's actual error message.

export interface Health {
  status: string
  version: string
  ai_provider: string
  ai_label: string            // plain words, e.g. "Ollama · qwen2.5:7b, on this computer"
  features: { talk?: boolean } // server switches; Talk is off until a good enough model is set
}

export interface Language {
  code: string
  name: string
  native_name: string
  script: string
  direction: 'ltr' | 'rtl'
  transliteration_supported: boolean
}

export interface UnitListItem {
  id: string
  title: string
  source_language: string
  target_language: string
  cefr_level: string | null
  vocabulary_count: number
  grammar_count: number
  exercise_count: number
  flashcard_count: number
  created_at: string
}

export interface ReadingPair { source: string; target: string }

export interface LessonUnit {
  id: string
  title: string
  source_language: string
  target_language: string
  support_language: string | null
  cefr_level: string | null
  source_document_ids: string[]
  vocabulary_ids: string[]
  grammar_ids: string[]
  exercise_ids: string[]
  flashcard_ids: string[]
  bilingual_reading: ReadingPair[]
  summary: string | null
  tags: string[]
  created_at: string
}

export interface VocabularyItem {
  id: string
  lemma: string
  surface: string
  target_language: string
  translations: Record<string, string[]>
  pos: string | null
  gender: 'm' | 'f' | 'n' | null
  transliteration: string | null
  example_text: string | null
  cefr_level: string | null
}

export interface GrammarPoint {
  id: string
  target_language: string
  name: string
  summary: string
  evidence: string[]
  cefr_level: string | null
  support_language: string | null
}

export interface Exercise {
  id: string
  type: string
  source_language: string
  target_language: string
  prompt: string
  expected_answer: string | null
  acceptable_answers: string[]
  choices: string[]
  hints: string[]
  explanation: string | null
  difficulty: number
  skill_tags: string[]
  grading_mode: string
}

export interface UnitDetail {
  id: string
  title: string
  source_language: string
  target_language: string
  support_language: string | null
  cefr_level: string | null
  summary: string | null
  bilingual_reading: ReadingPair[]
  tags: string[]
  vocabulary: VocabularyItem[]
  grammar: GrammarPoint[]
  exercises: Exercise[]
  flashcards: Card[]
}

export interface IngestSummary {
  unit_id: string
  document_id: string
  title: string
  source_language: string
  target_language: string
  vocabulary_count: number
  grammar_count: number
  exercise_count: number
  flashcard_count: number
  unit_path: string | null
}

export interface Card {
  id: string
  front: string
  back: string
  source_language: string
  target_language: string
  direction: string
  card_type: string
  interval: number
  ease_factor: number
  repetitions: number
  lapses: number
  needs_extra_review: boolean
  due_at: string
  // Course and Talk cards: the target-language side split out, so it can be spoken and shown per the
  // script-display setting. null for cards made from your own texts (use `back`).
  text: string | null
  tr: string | null
}

export interface ReviewResponse {
  card: Card
  interval_after: number
  ease_after: number
  repetitions_after: number
}

export interface MaterialsSource {
  name: string
  provider: string
  root: string
  read_only: boolean
  available: boolean
  notes: string | null
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  })
  if (!res.ok) {
    let detail = res.statusText
    try { detail = (await res.json()).detail ?? detail } catch { /* ignore */ }
    throw new Error(`${res.status} ${detail}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  health: () => request<Health>('/health'),
  languages: () => request<Language[]>('/languages'),
  units: (target?: string) =>
    request<UnitListItem[]>(`/units${target ? `?target=${target}` : ''}`),
  unit: (id: string) => request<LessonUnit>(`/units/${id}`),
  unitDetail: (id: string) => request<UnitDetail>(`/units/${id}/detail`),
  cardsDue: (target?: string, limit = 50) =>
    request<Card[]>(`/cards/due?${new URLSearchParams({ ...(target ? { target } : {}), limit: String(limit) })}`),
  // event_id makes the call idempotent, so an offline queue can replay it safely.
  reviewCard: (id: string, rating: number, eventId?: string, seconds?: number) =>
    request<ReviewResponse>(`/cards/${id}/review`, {
      method: 'POST', body: JSON.stringify({ rating, event_id: eventId ?? null, seconds: seconds ?? 0 }),
    }),
  deleteUnit: (id: string) => fetch(`/api/units/${id}`, { method: 'DELETE' }).then((r) => {
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
  }),
  // source_language is the language the pasted text is written in: the learner's own language (the lesson
  // translates it into the target) or the target language itself (native material, explained in support).
  ingestText: (body: {
    text: string
    title: string
    source_language: string
    target_language: string
    support_language?: string | null
    cefr_level?: string | null
    tags?: string[]
  }) => request<IngestSummary>('/ingest/text', { method: 'POST', body: JSON.stringify(body) }),
  materialsSources: () => request<MaterialsSource[]>('/materials/sources'),
  exportAnkiUrl: (target: string) => `/api/export/anki?target=${encodeURIComponent(target)}`,
}
