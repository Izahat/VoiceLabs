# VoiceLabs architecture

## Boundaries

```text
app/domain          Pure business entities and interfaces
app/services        Application workflows
infrastructure/api  HTTP adapters only
infrastructure/     Model runtime, persistence, and file storage
providers/          Composition root / dependency wiring
frontend/           Browser client
```

API handlers validate transport input, call application services, and
serialize responses. SQLAlchemy queries and filesystem layout rules belong to
`PersistenceService`, repositories, and `FileStorage`.

## Persistence model

```text
User
 ├── Job
 │    ├── source Asset
 │    └── output Asset
 ├── input/reference Assets
 └── VoiceProfile → reference Asset
```

SQLite stores durable metadata. Audio and video bytes are stored under
`STORAGE_DIR` and addressed by random asset IDs. Each asset stores its owner,
job, role, original filename, MIME type, size, and SHA-256 checksum.

The browser sends an `X-User-Id` value generated once and retained in
`localStorage`. This is a local-user identity mechanism, not authentication.
Production deployments should replace it with a real authenticated principal
and signed media URLs.

## Request lifecycle

```text
HTTP request
  → resolve user
  → create Job
  → stream upload to FileStorage
  → register Asset
  → execute media/AI pipeline
  → store generated Asset
  → update Job status and metadata
  → return asset URL
```

`database.py` creates the initial schema at startup. Repositories isolate
database operations, while `PersistenceService` coordinates database and file
storage. Alembic can be introduced later without changing API handlers.

## Active AI boundary

The production application currently wires only:

```text
Whisper Turbo ASR → transcription service
OmniVoice TTS    → voice design, cloning, and synthesis
```

Gemini translation and automatic video dubbing are not initialized and their
legacy endpoints return `410 Gone`. Speaker diarization is also disabled: the
transcription API returns `speakers: null` and marks the feature as planned.
Legacy orchestration and diarization implementation material is not part of
the active dependency graph.

## Model runtime

Whisper Turbo and OmniVoice are resolved with `huggingface_hub.snapshot_download`
into the standard Hugging Face cache (or `MODEL_CACHE_DIR`). Both adapters load
models lazily, keep them in memory for subsequent requests, inspect CUDA at
load time, and fall back to a CPU-compatible configuration when `auto` cannot
use an accelerator.
