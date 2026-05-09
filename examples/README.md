# Examples

Seed materials for the four MVP languages live in `content/inbox/`. Run any of these to generate a lesson:

```bash
lingua-agent ingest file --source en --target it content/inbox/en_to_it_coffee.md
lingua-agent ingest file --source en --target fa content/inbox/en_to_fa_university.md
lingua-agent ingest file --source en --target ru content/inbox/en_to_ru_book.md
lingua-agent ingest file --source it --target en content/inbox/it_to_en_caffe.md
lingua-agent ingest file --source fa --target en content/inbox/fa_to_en_doust.md
lingua-agent ingest file --source ru --target en content/inbox/ru_to_en_kniga.md
lingua-agent ingest file --source it --target fa --support en content/inbox/it_to_fa_biologia.md
```

Generated lesson units land in `content/units/`; flashcards land in the local data dir; review them with `lingua-agent review due`.

The bundled mock AI provider produces deterministic, schema-valid output without any network call. Real AI providers (Phase 5) will produce real translations and explanations.
