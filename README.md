# VoiceLabs

Локальное приложение для транскрибации и синтеза речи. Модели запускаются напрямую из Python-процесса, без Docker и без каталога `docker3/`.

## Что работает сейчас

- **ASR:** аудио и видео → текст, язык, сегменты и timestamps.
- **TTS Voice Design:** текст → голос OmniVoice по описанию: пол, возраст, pitch, стиль, accent.
- **Voice Cloning:** аудио или видео пользователя → сохранённый голосовой профиль → синтез нового текста.
- **URL transcription:** загрузка видео по URL и транскрибация.
- **Persistence:** пользователи, jobs, audio/video assets и voice profiles сохраняются в SQLite; большие бинарные файлы — в `data/storage`.

## Временно отключено

- Перевод текста через Gemini.
- Автоматический video dubbing: видео → перевод → новый голос → готовое видео.
- Speaker diarization: модель пока не выбрана и не подключена.

Старые dubbing endpoints сохранены для обратной совместимости, но отвечают `410 Gone` и не запускают pipeline. Они будут возвращены после отдельной реализации и тестирования.

## Модели

### Whisper Turbo — ASR

- Репозиторий: `deepdml/faster-whisper-large-v3-turbo-ct2`
- Формат: CTranslate2 для `faster-whisper`
- Реализация: `faster_whisper.WhisperModel`
- Модель загружается напрямую из Hugging Face cache.

### OmniVoice — TTS и Voice Cloning

- Репозиторий: `k2-fsa/OmniVoice`
- Voice Design и cloning
- Реализация: `omnivoice.models.omnivoice.OmniVoice`

## Cache моделей и проверка устройства

Whisper Turbo и OmniVoice используют один стандартный Hugging Face cache, как в `HybridVoice`:

- Linux/WSL: `~/.cache/huggingface/hub/`
- Windows: `C:\Users\<user>\.cache\huggingface\hub\`
- При необходимости путь задаётся через `MODEL_CACHE_DIR`.

При первом обращении `snapshot_download()` скачивает модель в этот cache. При следующих запусках тот же snapshot переиспользуется; повторной загрузки весов не происходит.

Оба адаптера проверяют устройство перед загрузкой модели:

- `DEVICE=auto` выбирает CUDA, если она доступна.
- При отсутствии или ошибке CUDA используется CPU.
- Whisper на CPU автоматически выбирает `int8`, на CUDA — `float16`.
- Реальное устройство и тип вычислений видны в логах и runtime-информации моделей.

## Архитектура

```text
frontend/                       Browser SPA
    │
    ▼
FastAPI (main.py, port 8000)
    ├── Transcription API ───── local faster-whisper Turbo
    ├── TTS/Clone API ───────── local OmniVoice
    └── PersistenceService ──── SQLite metadata + filesystem assets
```

Основные границы:

- `app/domain/` — entities и interfaces.
- `app/services/` — application services (`VoiceService`, transcription, persistence).
- `infrastructure/api/` — FastAPI adapters.
- `infrastructure/persistence/` — SQLAlchemy models/repositories.
- `infrastructure/storage/` — безопасное сохранение audio/video.
- `providers/` — dependency injection и composition root.
- `infrastructure/model_runtime.py` — общий Hugging Face cache и device selection.

## Требования

- Python 3.10+
- FFmpeg
- PyTorch; NVIDIA GPU рекомендуется для скорости, но runtime проверяет CUDA и умеет fallback на CPU.

## Запуск

### 1. Python API

```bash
python3 -m venv venv
source venv/bin/activate
# Для NVIDIA CUDA можно сначала установить CUDA-сборку PyTorch:
# pip install torch==2.5.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements.txt
cp .env.example .env
python3 main.py
```

### 2. Первый запуск моделей

Модели скачиваются автоматически при первом TTS или ASR-запросе и сохраняются в Hugging Face cache. `HybridVoice/` используется только как эталон архитектуры cache/device и не является runtime-зависимостью VoiceLabs.

## Конфигурация

Минимальные переменные находятся в `.env.example`:

```env
DATABASE_URL=sqlite+aiosqlite:///./data/voicelabs.db
STORAGE_DIR=./data/storage
WHISPER_MODEL_REPO=deepdml/faster-whisper-large-v3-turbo-ct2
OMNIVOICE_MODEL=k2-fsa/OmniVoice
MODEL_CACHE_DIR=
HF_TOKEN=
AI_DEVICE=auto
WHISPER_DEVICE=auto
WHISPER_COMPUTE_TYPE=auto
```

Секреты не добавляются в Git. `.env` и `data/` находятся в `.gitignore`.

## Active API

### Transcription

- `GET /api/v1/transcription/health`
- `POST /api/v1/transcription/transcribe` — audio/video upload.
- `POST /api/v1/transcription/transcribe/url` — URL download + ASR.
- `GET /api/v1/transcription/supported-platforms`

Ответ ASR содержит `language`, `full_text`, `segments`, `duration`. Поле `speakers` сейчас равно `null`; ответ также сообщает `diarization.status=planned`.

### OmniVoice TTS

- `POST /api/v1/dubbing/tts/voice-design` — синтетический голос по параметрам.
- `POST /api/v1/dubbing/tts/clone` — создать voice profile из audio/video.
- `POST /api/v1/dubbing/tts/synthesize` — синтез текста сохранённым профилем.
- `GET /api/v1/dubbing/languages`
- `GET /api/v1/dubbing/voices`

### Persistence

- `GET /api/v1/dubbing/jobs` — история текущего local user.
- `GET /api/v1/dubbing/status/{job_id}` — состояние job.
- `GET /api/v1/dubbing/assets/{asset_id}` — audio/video asset.

Frontend создаёт `X-User-Id` и сохраняет его в `localStorage`. Это локальный идентификатор, не полноценная авторизация.

## Roadmap

В следующих этапах будут реализованы отдельно и только после тестирования:

1. Перевод транскрипта через выбранную локальную или внешнюю LLM с контролем качества.
2. Автоматический video dubbing с сохранением таймингов, несколькими голосами и muxing через FFmpeg.
3. Speaker diarization после выбора и валидации модели, затем привязка спикеров к ASR-сегментам.
4. Настоящая авторизация, signed URLs для media assets и миграции Alembic.

## Проверки

```bash
python -m unittest discover -s tests -v
python -m compileall app config infrastructure providers main.py
```

Первый запуск моделей требует сети Hugging Face; последующие запуски используют локальный cache.

## License

Private project.
