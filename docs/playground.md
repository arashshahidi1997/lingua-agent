# Playground UI

The `lingua-agent playground` command opens a local browser UI on top of the existing core. Use it for clicking through ingest → lessons → review → tutor without typing CLI commands.

> **Not the production UI.** The real product UI is the FastAPI + React PWA planned in Phase 8 — see [`clients.md`](clients.md). The playground is the iteration / demo / "let me actually try this" tool, which is how every Python AI project ships internal tools (Hugging Face Spaces, OpenAI, Anthropic, Cohere all use Streamlit/Gradio for this).

## Install + launch

```bash
pip install -e ".[playground]"   # adds Streamlit
lingua-agent playground          # opens http://localhost:8501 in your browser
```

Useful flags:

```bash
lingua-agent playground --port 8765
lingua-agent playground --no-open   # headless, don't open the browser
```

## What's in it

- **Sidebar**: language pair selector (source / target / optional support), provider info, data + content directory paths. RTL languages auto-warn so you know the lesson + review panes will flip direction.
- **📥 Ingest**: paste any text → choose level → click *Ingest*. Runs the same pipeline as `lingua-agent ingest text`. Shows the bilingual reading, vocabulary, exercise count, and the markdown path the lesson was written to.
- **📖 Lessons**: lists every `LessonUnit` from your data dir. Expand to see summary + bilingual reading; tick a box to view the canonical markdown.
- **🃏 Review**: the SRS queue. Shows one card at a time, "Show back" reveal, then 0–5 quality buttons that drive the SM-2 scheduler exactly the way `lingua-agent review answer` does. Includes a one-click Anki CSV export.
- **🤖 Tutor**: a chat with the tutor agent. Uses the configured provider — with `LINGUA_AI_PROVIDER=mock` you get the canned mock response; switch to OpenAI / Gemma / Qwen / Ollama via env vars (see [`providers.md`](providers.md)) for real conversation.

## Persian / RTL

Every place that renders target-language text wraps it in `<div dir="rtl" style="text-align: right;">…</div>` when the target language is RTL. So Persian content shows as Persian, right-aligned, without bidi hiccups, in the bilingual reading, in the lesson list, in the review front/back, and in the tutor chat.

## Why Streamlit (and not Gradio / Tauri / Electron)

- **Streamlit** is what teams ship internally for AI/ML tool prototyping. Hugging Face's internal tools, Anthropic's eval dashboards, OpenAI's data-tooling — all on Streamlit / Gradio. Right tool for "iterate today on a Python core". Single file, no build step, no native packaging.
- **Gradio** is similar; we picked Streamlit because the SRS review pane benefits from explicit per-component state (Gradio's reactive paradigm makes the "show back → grade → next card" loop awkward).
- **Tauri / Electron** are wrappers around a real frontend (React / Svelte). They're the answer for shipping a desktop binary in Phase 8b — not for "let me click around tomorrow".
- **Jupyter / Voila** could work but the multi-tab review/tutor UI is a worse fit than Streamlit's primitives.
