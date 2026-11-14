// API contract for the Product v2 features (docs/product-v2.md): courses and the
// Path, exercises, practice, Today, stories, Talk, speech, recordings, and audio.
// Mirrors src/lingua_agent/api/course_routes.py and course_schemas.py.

import type { Card } from './api'

// ---- shared ---------------------------------------------------------------

/** One piece of target-language text with its transliteration and meaning. */
export interface Item {
  id: string
  text: string        // target language (e.g. Persian script)
  tr: string | null   // transliteration
  gloss: string       // support-language meaning
  note?: string | null
}

// ---- courses / Path -------------------------------------------------------

export type LessonState = 'locked' | 'current' | 'done'

export interface LessonSummary {
  id: string
  title: string
  kind: 'script' | 'words' | 'phrases' | 'grammar'
  item_count: number
  state: LessonState
  best_score: number | null   // 0..1
}

export interface UnitSummary {
  id: string
  title: string
  goal: string
  lessons: LessonSummary[]
  story_id: string | null
  scenario_id: string | null
  story_unlocked: boolean     // the unit is the first one, or has a lesson done
  scenario_unlocked: boolean
  quiz_state: LessonState     // checkpoint quiz; 'current' once all lessons are done
  done: boolean
}

export interface CourseSummary {
  id: string
  title: string
  description: string
  target: string
  support: string
  level: string
  progress: number            // 0..1, lessons done / lessons total
  lessons_done: number
  lessons_total: number
}

export interface Course extends CourseSummary {
  units: UnitSummary[]
  next_lesson: { unit_id: string; lesson_id: string; title: string; unit_title: string } | null
}

export interface LessonDetail {
  id: string
  unit_id: string
  title: string
  kind: LessonSummary['kind']
  note: string | null         // markdown, support language
  items: Item[]
}

// ---- exercises ------------------------------------------------------------

/**
 * A session is an ordered list of exercises. The client grades locally
 * (answers are included) and reports results on completion.
 *
 * - intro:         present `item` (text, tr, gloss, audio). No answer.
 * - choose_gloss:  show item.text (+ tr unless hide_tr), pick the gloss from `choices`.
 * - choose_text:   show item.gloss, pick the target text from `choices`.
 * - listen:        play item.text audio only, pick the target text from `choices`.
 * - match:         match `pairs` (text ↔ gloss); all pairs must be matched.
 * - order:         build item.text from `tiles` (target-language words, shuffled); prompt is item.gloss.
 * - type_tr:       show item.text, type its transliteration; compare with `answer` leniently
 *                  (lowercase, strip â→a, punctuation, spaces, hyphens).
 */
export type ExerciseKind = 'intro' | 'choose_gloss' | 'choose_text' | 'listen' | 'match' | 'order' | 'type_tr'

export interface CourseExercise {
  id: string
  kind: ExerciseKind
  item: Item | null           // null only for 'match'
  choices: string[]           // choose_gloss → glosses; choose_text / listen → target texts
  answer: string | null       // the correct choice / full ordered text / transliteration
  pairs: Item[]               // match only
  tiles: string[]             // order only
  hide_tr: boolean
}

export interface ExerciseSession {
  id: string                  // lesson id, unit quiz id ("<unit>:quiz") or "practice"
  title: string
  course_id: string
  target: string              // language of item.text, for speech and text direction
  exercises: CourseExercise[]
}

export interface ItemResult { item_id: string; correct: boolean }

export interface CompleteRequest {
  results: ItemResult[]
  seconds: number             // time spent, for the daily goal
}

export interface CompleteResponse {
  score: number               // 0..1
  passed: boolean             // score >= 0.7 for quizzes; lessons always pass
  cards_added: number         // flashcards created from the lesson's items
  unlocked: string | null     // id of the next lesson / quiz unlocked
}

// ---- Today ----------------------------------------------------------------

export interface Today {
  course: CourseSummary | null
  next_lesson: Course['next_lesson']
  due_count: number           // flashcards due for this target language
  learned_count: number       // items introduced so far
  minutes_today: number
  daily_goal_minutes: number
  streak_days: number         // consecutive days with activity (shown only if the user enables it)
  story: StorySummary | null      // suggested story (current unit, or latest unlocked)
  scenario: ScenarioSummary | null
}

// ---- stories & dialogues ----------------------------------------------------

export interface Speaker { name: string; voice: 'male' | 'female' }

export interface StorySummary {
  id: string
  course_id: string
  unit_id: string
  kind: 'story' | 'dialogue'
  title: string
  title_gloss: string
  line_count: number
  unlocked: boolean           // its unit has at least one lesson done (or it is unit 1)
}

export interface StoryLine extends Item { speaker: string }

export interface Story extends StorySummary {
  speakers: Record<string, Speaker>
  lines: StoryLine[]
}

// ---- Talk -------------------------------------------------------------------

export interface ScenarioSummary {
  id: string
  course_id: string
  unit_id: string
  title: string
  title_target: string
  goal: string
  unlocked: boolean
}

export interface Scenario extends ScenarioSummary {
  setting: string
  persona: string
  persona_name: string        // short display name, e.g. "Maryam"
  opener: Item
  useful: Item[]
}

/** One assistant turn: what the character says, plus a gentle correction of the learner's last message. */
export interface TalkTurn {
  text: string
  tr: string | null
  gloss: string | null
  correction: string | null   // support language; null when the learner's message was fine
  better: string | null       // a corrected / more natural version of the learner's message (target language)
}

export interface TalkMessage {
  role: 'user' | 'assistant'
  content: string             // user: what they typed; assistant: turn.text
  turn: TalkTurn | null       // assistant only
  created_at: string
}

export interface TalkSession {
  id: string
  scenario: Scenario | null   // null = free conversation
  target: string
  support: string
  messages: TalkMessage[]
  ended: boolean
}

export interface TalkSummary {
  went_well: string
  mistakes: { you_said: string; better: string; note: string }[]
  new_words: Item[]
  cards_added: number
}

// ---- speech, recordings, audio ---------------------------------------------

export interface SpeechInfo {
  server_tts: Record<string, boolean>   // language → a server voice is installed
  stt: boolean                          // server-side transcription available
}

export interface Recording {
  id: string
  ref: string                 // what it belongs to: an item id, "story:<id>:<line>", or "diary"
  language: string
  mime_type: string
  seconds: number | null
  created_at: string
  url: string                 // GET for the audio
}

export interface Cue { start: number; end: number; text: string; tr?: string | null; gloss?: string | null }

export interface AudioTrack {
  id: string
  title: string
  language: string
  mime_type: string
  source: 'upload' | 'materials'
  has_transcript: boolean
  created_at: string
  url: string
}

export interface AudioTrackDetail extends AudioTrack {
  cues: Cue[]
}

// ---- client ---------------------------------------------------------------

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const isForm = init?.body instanceof FormData
  const res = await fetch(`/api${path}`, {
    ...init,
    headers: isForm ? init?.headers : { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  })
  if (!res.ok) {
    let detail = res.statusText
    try { detail = (await res.json()).detail ?? detail } catch { /* ignore */ }
    throw new Error(`${res.status} ${detail}`)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

const post = <T>(path: string, body?: unknown) =>
  req<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) })

const q = (params: Record<string, string | number | undefined | null>) => {
  const p = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null) p.set(k, String(v))
  const s = p.toString()
  return s ? `?${s}` : ''
}

export const courseApi = {
  // courses / Path
  courses: (target?: string, support?: string) => req<CourseSummary[]>(`/courses${q({ target, support })}`),
  course: (id: string) => req<Course>(`/courses/${id}`),
  lesson: (courseId: string, lessonId: string) => req<LessonDetail>(`/courses/${courseId}/lessons/${lessonId}`),
  lessonSession: (courseId: string, lessonId: string) =>
    req<ExerciseSession>(`/courses/${courseId}/lessons/${lessonId}/session`),
  completeLesson: (courseId: string, lessonId: string, body: CompleteRequest) =>
    post<CompleteResponse>(`/courses/${courseId}/lessons/${lessonId}/complete`, body),
  unitQuiz: (courseId: string, unitId: string) => req<ExerciseSession>(`/courses/${courseId}/units/${unitId}/quiz`),
  completeUnitQuiz: (courseId: string, unitId: string, body: CompleteRequest) =>
    post<CompleteResponse>(`/courses/${courseId}/units/${unitId}/quiz/complete`, body),

  // practice: mixed exercises from learned items, weakest and due first
  practice: (courseId: string, n = 12) => req<ExerciseSession>(`/courses/${courseId}/practice${q({ n })}`),
  completePractice: (courseId: string, body: CompleteRequest) =>
    post<CompleteResponse>(`/courses/${courseId}/practice/complete`, body),

  // Today
  today: (target: string, support: string) => req<Today>(`/today${q({ target, support })}`),

  // stories
  stories: (target: string, support: string) => req<StorySummary[]>(`/stories${q({ target, support })}`),
  story: (id: string) => req<Story>(`/stories/${id}`),

  // Talk
  scenarios: (target: string, support: string) => req<ScenarioSummary[]>(`/scenarios${q({ target, support })}`),
  scenario: (id: string) => req<Scenario>(`/scenarios/${id}`),
  openTalk: (body: { target: string; support: string; scenario_id?: string | null }) =>
    post<TalkSession>('/talk/sessions', body),
  talk: (id: string) => req<TalkSession>(`/talk/sessions/${id}`),
  sayTalk: (id: string, content: string) => post<TalkMessage>(`/talk/sessions/${id}/messages`, { content }),
  endTalk: (id: string) => post<TalkSummary>(`/talk/sessions/${id}/end`),

  // speech. ttsUrl returns 404 when no server voice is installed: fall back to speechSynthesis.
  speech: () => req<SpeechInfo>('/speech'),
  ttsUrl: (text: string, lang: string) => `/api/tts${q({ lang, text })}`,

  // recordings (the learner's own voice)
  recordings: (ref?: string, refPrefix?: string) =>
    req<Recording[]>(`/recordings${q({ ref, ref_prefix: refPrefix })}`),
  addRecording: (blob: Blob, ref: string, language: string, seconds?: number) => {
    const f = new FormData()
    f.append('file', blob, 'recording.webm')
    f.append('ref', ref)
    f.append('language', language)
    if (seconds !== undefined) f.append('seconds', String(seconds))
    return req<Recording>('/recordings', { method: 'POST', body: f })
  },
  deleteRecording: (id: string) => req<void>(`/recordings/${id}`, { method: 'DELETE' }),

  // audio from sources (uploads, or files from a materials source)
  audio: () => req<AudioTrack[]>('/audio'),
  audioTrack: (id: string) => req<AudioTrackDetail>(`/audio/${id}`),
  uploadAudio: (file: File, opts: { title?: string; language: string; transcript?: File | null }) => {
    const f = new FormData()
    f.append('file', file)
    f.append('language', opts.language)
    if (opts.title) f.append('title', opts.title)
    if (opts.transcript) f.append('transcript', opts.transcript)
    return req<AudioTrack>('/audio', { method: 'POST', body: f })
  },
  audioFromMaterials: (body: { source: string; path: string; language: string; title?: string }) =>
    post<AudioTrack>('/audio/from-materials', body),
  transcribeAudio: (id: string) => post<AudioTrackDetail>(`/audio/${id}/transcribe`),  // 501 if no STT installed
  deleteAudio: (id: string) => req<void>(`/audio/${id}`, { method: 'DELETE' }),
}

export type { Card }
