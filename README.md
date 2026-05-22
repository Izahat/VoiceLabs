# Dublaj — Автоматический дубляж видео

Система автоматического дубляжа видео с использованием AI: распознавание речи, перевод и синтез речи с клонированием голоса. Работает полностью локально на GPU (NVIDIA CUDA).

## Возможности

- **Voice Cloning** — тот же голос диктора, но на другом языке
- **Voice Design** — синтетический голос по описанию (мужской/женский)
- **600+ языков** — поддержка большинства языков мира
- **Audio Separation** — извлечение чистого голоса из видео с музыкой
- Полностью локально — данные не уходят в облако

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                  Dublaj App (порт 8000)                      │
│                    FastAPI + Python                           │
└──────────┬──────────┬──────────┬──────────┬─────────────────┘
           │          │          │          │
           ▼          ▼          ▼          ▼
     ┌──────────┐ ┌────────┐ ┌──────────┐ ┌────────────────┐
     │ Whisper  │ │ Gemini │ │ OmniVoice│ │ Audio Separator│
     │порт 8100 │ │  API   │ │порт 8200 │ │   порт 8300    │
     │  (Docker)│ │(Google)│ │ (Docker) │ │   (Docker)     │
     └──────────┘ └────────┘ └──────────┘ └────────────────┘
```

### Порты сервисов

| Сервис | Порт | Назначение |
|--------|------|------------|
| **Dublaj App** | 8000 | Основное приложение |
| **Whisper** | 8100 | Распознавание речи (транскрибация) |
| **OmniVoice** | 8200 | Синтез речи (TTS + Voice Cloning) |
| **Audio Separator** | 8300 | Разделение голоса и музыки |

## Требования

- **ОС:** Ubuntu / Debian / WSL2 (Windows)
- **GPU:** NVIDIA с поддержкой CUDA (8+ GB VRAM)
- **Docker:** Docker + Docker Compose + NVIDIA Container Toolkit
- **Python:** 3.10+
- **FFmpeg:** системная установка

## Установка

### 1. Клонировать репозиторий

```bash
git clone https://github.com/ТВОЙ_ЮЗЕР/dublaj.git
cd dublaj
```

### 2. Установить системные зависимости

```bash
# FFmpeg (Ubuntu/Debian/WSL)
sudo apt update && sudo apt install -y ffmpeg

# Проверить установку
ffmpeg -version
```

### 3. Установить Python-зависимости

```bash
python3 -m venv venv
source venv/bin/activate        # Linux
source venv/bin/activate.fish   # Fish shell

pip install -r requirements.txt
```

### 4. Настроить `.env`

```bash
cp .env.example .env
```

Отредактируйте `.env`:

```env
# --- General ---
APP_HOST=0.0.0.0
APP_PORT=8000
TEMP_DIR=./tmp
OUTPUT_DIR=./output

# --- Whisper (Docker, порт 8100) ---
WHISPER_BASE_URL=http://localhost:8100
WHISPER_ENDPOINT=/v1/audio/transcriptions

# --- Translation ---
TRANSLATION_PROVIDER=gemini
GEMINI_API_KEY=ВАШ_GEMINI_API_KEY
TRANSLATION_MODEL=gemini-2.5-flash

# --- OmniVoice TTS (Docker, порт 8200) ---
OMNIVOICE_URL=http://localhost:8200
OMNIVOICE_VOICE=female

# --- Audio Separator (Docker, порт 8300) ---
AUDIO_SEPARATOR_URL=http://localhost:8300
USE_VOICE_SEPARATION=true

# --- FFmpeg ---
FFMPEG_PATH=ffmpeg
```

> **Gemini API Key** — единственный внешний сервис. Получить бесплатно: [Google AI Studio](https://aistudio.google.com/apikey)

## Запуск Docker-сервисов

Все модели скачиваются автоматически в Docker volumes при первом запуске. Повторные запуски — мгновенные.

### Whisper (порт 8100) — распознавание речи

```bash
docker compose -f docker3/docker-compose.whisper.yml up -d
```

Модель `faster-whisper-large-v3` скачивается в volume `whisper-model-data`.

### OmniVoice (порт 8200) — синтез речи

```bash
docker compose -f docker3/docker-compose.omnivoice.yml up -d --build
```

Модель `k2-fsa/OmniVoice` скачивается из HuggingFace в volume `omnivoice-model-data`.

### Audio Separator (порт 8300) — разделение голоса

```bash
docker compose -f docker3/docker-compose.audio-separator.yml up -d --build
```

Модель `melband_roformer_big_beta4` скачивается в volume `audio-separator-model-data`.

### Запустить все сервисы одной командой

```bash
docker compose \
  -f docker3/docker-compose.whisper.yml \
  -f docker3/docker-compose.omnivoice.yml \
  -f docker3/docker-compose.audio-separator.yml \
  up -d --build
```

### Проверить что всё запущено

```bash
docker ps
```

Должны быть видны 3 контейнера:

```
dublaj-whisper              0.0.0.0:8100->8000/tcp
dublaj-omnivoice            0.0.0.0:8200->8200/tcp
dublaj-audio-separator      0.0.0.0:8300->8300/tcp
```

### Проверить здоровье сервисов

```bash
curl http://localhost:8100/health
curl http://localhost:8200/health
curl http://localhost:8300/health
```

## Запуск приложения

```bash
source venv/bin/activate
python3 main.py
```

Открыть в браузере: **http://localhost:8000/docs** (Swagger UI)

## Использование

### Voice Cloning — тот же голос, другой язык

Голос диктора сохраняется — тембр, интонация, эмоции.

```bash
curl -X POST "http://localhost:8000/api/v1/dubbing/clone/download" \
  -F "video=@video.mp4" \
  -F "target_language=ru" \
  --output dubbed_ru.mp4
```

### Voice Design — новый голос

Синтетический голос по описанию (male/female).

```bash
curl -X POST "http://localhost:8000/api/v1/dubbing/process/download" \
  -F "video=@video.mp4" \
  -F "target_language=az" \
  --output dubbed_az.mp4
```

### Поддерживаемые языки (ISO 639-1)

| Код | Язык | Код | Язык | Код | Язык |
|-----|------|-----|------|-----|------|
| `az` | Азербайджанский | `tr` | Турецкий | `ru` | Русский |
| `en` | Английский | `es` | Испанский | `fr` | Французский |
| `de` | Немецкий | `it` | Итальянский | `pt` | Португальский |
| `zh` | Китайский | `ja` | Японский | `ko` | Корейский |
| `ar` | Арабский | `hi` | Хинди | `uk` | Украинский |
| `kk` | Казахский | `uz` | Узбекский | `ka` | Грузинский |

Полный список 600+ языков: `GET http://localhost:8200/languages`

## API Endpoints

| Endpoint | Метод | Режим | Описание |
|----------|-------|-------|----------|
| `/docs` | GET | — | Swagger документация |
| `/api/v1/dubbing/health` | GET | — | Health check |
| `/api/v1/dubbing/process` | POST | Voice Design | JSON результат |
| `/api/v1/dubbing/process/download` | POST | Voice Design | Скачать видео |
| `/api/v1/dubbing/clone` | POST | Voice Cloning | JSON результат |
| `/api/v1/dubbing/clone/download` | POST | Voice Cloning | Скачать видео |

## Управление Docker

```bash
# Остановить все сервисы
docker compose -f docker3/docker-compose.whisper.yml down
docker compose -f docker3/docker-compose.omnivoice.yml down
docker compose -f docker3/docker-compose.audio-separator.yml down

# Логи конкретного сервиса
docker logs -f dublaj-whisper
docker logs -f dublaj-omnivoice
docker logs -f dublaj-audio-separator

# Удалить volumes (модели скачаются заново)
docker volume rm whisper-model-data omnivoice-model-data audio-separator-model-data
```

## Структура проекта

```
dublaj/
├── main.py                              # Точка входа
├── config/settings.py                   # Конфигурация (.env)
├── providers/service_factory.py         # Dependency Injection
├── app/
│   ├── domain/
│   │   ├── entities.py                  # Сущности
│   │   └── interfaces.py                # Абстрактные интерфейсы
│   └── services/
│       └── dubbing_orchestrator.py      # Бизнес-логика
├── infrastructure/
│   ├── api/dubbing_router.py            # HTTP эндпоинты
│   ├── whisper_transcriber.py           # Клиент Whisper
│   ├── llm_translator.py                # Клиент Gemini
│   ├── omnivoice_tts_synthesizer.py     # Клиент OmniVoice
│   ├── audio_separator_client.py        # Клиент Audio Separator
│   └── ffmpeg_audio_mixer.py            # FFmpeg обёртка
├── docker3/
│   ├── docker-compose.whisper.yml       # Whisper (8100)
│   ├── docker-compose.omnivoice.yml     # OmniVoice (8200)
│   ├── docker-compose.audio-separator.yml # Audio Separator (8300)
│   ├── Dockerfile.omnivoice             # Dockerfile OmniVoice
│   ├── Dockerfile.audio-separator       # Dockerfile Audio Separator
│   ├── server_omnivoice.py              # OmniVoice сервер
│   ├── server_audio_separator.py        # Audio Separator сервер
│   └── requirements.omnivoice.txt       # Зависимости OmniVoice
├── .env                                 # Конфигурация
├── requirements.txt                     # Python зависимости
└── HOW_WORKS.md                         # Подробная документация
```

## Troubleshooting

### GPU не работает

```bash
# Проверить GPU внутри контейнера
docker exec -it dublaj-whisper nvidia-smi

# Установить NVIDIA Container Toolkit (если не установлен)
# Ubuntu/Debian:
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
sudo apt install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### PYTHONPATH ошибка в WSL

```bash
# Используйте абсолютный путь:
PYTHONPATH=/mnt/c/Users/User/Desktop/dublaj python3 main.py
```

### Модель не скачивается

```bash
# Проверить логи model-downloader:
docker logs dublaj-whisper-model-downloader
docker logs dublaj-omnivoice-model-downloader
docker logs dublaj-audio-separator-model-downloader
```

## Лицензия

Private project.
