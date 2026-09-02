# VoiceLabs — Контекст проекта

## Что делает проект
VoiceLabs — система для обработки аудио/видео: разделение спикеров (diarization), транскрипция, клонирование голоса, перевод. Работает через Docker микросервисы.

---

## Что мы делали: GPU ускорение для PyAnnote Diarization

### Цель
Заставить PyAnnote speaker diarization работать на **GPU** БЕЗ обновления NVIDIA драйверов (CUDA 12.5).

### Проблема
PyAnnote работал на CPU, потому что PyTorch 2.1.0 (без CUDA варианта) был несовместим с драйвером CUDA 12.5.

---

## Шаги решения и ошибки

### Шаг 1: Обновили PyTorch в Dockerfile.pyannote
- Заменили `torch==2.1.0` на `torch==2.5.1+cu124` (CUDA 12.4 runtime, совместим с драйвером 12.5)
- Добавили `--extra-index-url https://download.pytorch.org/whl/cu124`

**Почему cu124:** Драйвер CUDA 12.5 обратно совместим — поддерживает любой CUDA runtime <= 12.5

### Ошибка 1: `pyannote.audio` требует `torch>=2.8.0`
- Последняя версия pyannote.audio потянула torch 2.8.0, который скачал cuda-toolkit 13.0.2
- Пакет `nvidia-cufft==12.0.0.61` дал **hash mismatch** — сборка упала
- **Решение:** Закрепили `pyannote.audio==3.1.1` (старая версия, совместимая с torch 2.5.1)

### Ошибка 2: `np.NaN was removed in the NumPy 2.0 release`
- `pyannote.audio==3.1.1` использует `np.NaN`, который удалён в numpy 2.0
- **Решение:** Добавили `"numpy<2"` в pip install

### Ошибка 3: `Pipeline.from_pretrained() got an unexpected keyword argument 'token'`
- `pyannote.audio==3.1.1` использует `use_auth_token`, а не `token`
- **Решение:** Заменили `token=HF_TOKEN` на `use_auth_token=HF_TOKEN` в server_pyannote.py

### Ошибка 4: `hf_hub_download() got an unexpected keyword argument 'use_auth_token'`
- Старый pyannote.audio передаёт `use_auth_token` в `huggingface_hub`, но новая версия huggingface_hub ждёт `token`
- **Решение:** Закрепили `"huggingface_hub<0.26"` (старая версия, поддерживающая `use_auth_token`)

### Ошибка 5: `SpeakerDiarization.__init__() got an unexpected keyword argument 'plda'`
- Модель `speaker-diarization-community-1` на HuggingFace обновилась и использует параметр `plda`
- `pyannote.audio==3.1.1` не знает про `plda`
- **Нельзя решить** закреплением версий — модель и старый код несовместимы

### Финальное решение: стратегия `--no-deps` → установка всех зависимостей
1. Ставим pyannote.audio с `--no-deps` (код последний, знает про `plda`, но не тянет torch 2.8)
2. Ставим torch==2.5.1+cu124 отдельно
3. Ставим все остальные зависимости вручную

**Проблема этого подхода:** недостающие зависимости появлялись одна за другой:
- `ModuleNotFoundError: No module named 'einops'` → добавили `einops`
- `ModuleNotFoundError: No module named 'lightning'` → добавили `lightning`
- `ModuleNotFoundError: No module named 'torch_audiomentations'` → добавили `torch-audiomentations`

### Альтернативный подход (последний, текущий в Dockerfile):
1. **Шаг 1:** `pip install pyannote.audio` — pip сам разрешает ВСЕ зависимости (не нужно угадывать)
2. **Шаг 2:** `pip install --force-reinstall torch==2.5.1 torchaudio==2.5.1 --extra-index-url .../cu124` — перезаписываем torch на совместимый с GPU

**Риск:** на шаге 1 может быть hash mismatch на nvidia-cufft (как в ошибке 1). Если будет — нужен подход с `--no-deps`.

---

## Изменённые файлы

### docker3/Dockerfile.pyannote
- Обновлён torch: `2.1.0` → `2.5.1+cu124`
- Два варианта установки зависимостей (см. текущее состояние файла)

### docker3/server_pyannote.py
- Параметр HF токена: менялся между `token=` и `use_auth_token=` в зависимости от версии pyannote
- **Текущее состояние:** `token=HF_TOKEN` (для последней версии pyannote.audio)
- GPU логика (строки 49-56): проверяет `torch.cuda.is_available()`, отправляет pipeline на GPU, fallback на CPU

### docker3/docker-compose.pyannote.yml
- Аналогично: параметр токена в model-downloader сервисе
- **Текущее состояние:** `token=token`
- GPU конфигурация уже была настроена (`deploy.resources.reservations.devices`)

---

## Текущий статус
- Dockerfile обновлён до подхода "установить всё + force-reinstall torch"
- Нужно запустить билд и проверить:
  1. `docker exec -it dublaj-pyannote-diarization python3 -c "import torch; print('CUDA:', torch.cuda.is_available())"`
  2. `curl http://localhost:8400/health` — должно быть `gpu_available: true`

## Команда для запуска
```bash
HF_TOKEN=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 docker compose -f docker3/docker-compose.pyannote.yml build --no-cache && \
HF_TOKEN=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 docker compose -f docker3/docker-compose.pyannote.yml up -d
```

---

## Ключевые правила
- **CUDA runtime <= CUDA version драйвера** — драйвер 12.5 поддерживает CUDA 12.4, 12.1, 11.8 и ниже
- **Docker Compose V2:** `--no-cache` работает только с `build` субкомандой, НЕ с `up`
- **HF_TOKEN** нужно передавать инлайн: `HF_TOKEN=xxx docker compose ...`
- **PyAnnote модель** на HuggingFace обновляется независимо от библиотеки — может ломать совместимость со старыми версиями pyannote.audio
