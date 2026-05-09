// Tiny typed fetch wrapper around the FastAPI backend.
// Every endpoint returns JSON; on non-2xx we throw with the response body
// so the UI can show the backend's actual error message.

export interface Health {
  status: string
  version: string
  ai_provider: string
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
}

export interface ReviewResponse {
  card: Card
  interval_after: number
  ease_after: number
  repetitions_after: number
}

export interface SessionMessage {
  role: 'system' | 'user' | 'assistant' | 'tool'
  content: string
  name?: string | null
  created_at: string
}

export interface TutorSession {
  id: string
  source_language: string
  target_language: string
  support_language: string | null
  messages: SessionMessage[]
  created_at: string
  updated_at: string
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
  cardsDue: (target?: string, limit = 50) =>
    request<Card[]>(`/cards/due?${new URLSearchParams({ ...(target ? { target } : {}), limit: String(limit) })}`),
  reviewCard: (id: string, rating: number) =>
    request<ReviewResponse>(`/cards/${id}/review`, {
      method: 'POST', body: JSON.stringify({ rating }),
    }),
  ingestText: (body: {
    text: string
    title: string
    source_language: string
    target_language: string
    support_language?: string | null
    cefr_level?: string | null
    tags?: string[]
  }) => request<IngestSummary>('/ingest/text', { method: 'POST', body: JSON.stringify(body) }),
  openSession: (body: { source_language: string; target_language: string; support_language?: string | null }) =>
    request<TutorSession>('/tutor/sessions', { method: 'POST', body: JSON.stringify(body) }),
  getSession: (id: string) => request<TutorSession>(`/tutor/sessions/${id}`),
  sendMessage: (id: string, content: string) =>
    request<{ role: string; content: string; created_at: string }>(
      `/tutor/sessions/${id}/messages`, { method: 'POST', body: JSON.stringify({ content }) },
    ),
  exportAnkiUrl: (target: string) => `/api/export/anki?target=${encodeURIComponent(target)}`,
}
