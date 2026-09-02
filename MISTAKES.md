# MISTAKES.md — Ошибки и решения при настройке PyAnnote Docker

## 1. pyannote.audio не найден (ModuleNotFoundError)
**Проблема:** При установке pyannote.audio в docker образе получали ошибку "Could not find a version that satisfies the requirement pyannote.audio"

**Причина:** Использовали `python:3.10-slim` базовый образ — в нём нет pyannote и его зависимостей.

**Решение:** Использовать `nvidia/cuda:12.5.0-runtime-ubuntu22.04` как базовый образ, так как PyAnnote требует PyTorch с CUDA.

---

## 2. ResolutionImpossible — конфликт зависимостей
**Проблема:** pip не мог разрешить зависимости при установке всех пакетов вместе.

**Причина:** Строгое указание версий torch, torchaudio, pyannote.audio — всё с разными зависимостями.

**Решение:** Разделить установку на ДВА отдельных RUN:
```dockerfile
RUN pip install torch==2.1.0 torchaudio==2.1.0
RUN pip install pyannote.audio fastapi uvicorn[standard] python-multipart pydantic python-dotenv
```

---

## 3. SHA256 hash mismatch для torch
**Проблема:** `ERROR: THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE`

**Причина:** torch==2.0.1+cu118 на download.pytorch.org обновился, а локальный кэш содержит старый хэш.

**Решение:** Не использовать строгую версию с CUDA спецификацией (cu118), а просто torch==2.1.0 — pip сам возьмёт нужный пакет с PyPI.

---

## 4. CUDA driver too old (found version 12050)
**Проблема:** PyTorch определяет драйвер NVIDIA как слишком старый для GPU режима.

**Причина:** Драйвер 555.97 = CUDA 12.5, но PyTorch 2.x скомпилирован с более новыми версиями CUDA toolkit.

**Решение:** Это WARNING, не ошибка — PyAnnote автоматически переключается на CPU. GPU работать НЕ БУДЕТ пока не обновишь драйвер NVIDIA (или используй PyTorch 2.0.1 с cu118 как минимум).

---

## 5. HF_TOKEN access denied (403 Forbidden)
**Проблема:** HuggingFace токен отклоняется при доступе к pyannote/speaker-diarization-community-1

**Причина:** Старый токен не имел доступа к gated репозиториям.

**Решение:** Создать новый fine-grained токен с правами "Read access to contents of all public gated repos you can access" на huggingface.co.

---

## 6. pip --index-url vs --extra-index-url
**Проблема:** При использовании `--index-url` PyPI полностью заменялся, и pyannote.audio не находился.

**Причина:** `--index-url` заменяет PyPI, а `--extra-index-url` добавляет к PyPI как fallback.

**Решение:** Использовать `--extra-index-url` для дополнительных индексов (как download.pytorch.org).

---
 
## 7. CUDA VersionMismatch
**Проблема:** `The NVIDIA driver on your system is too old` — PyTorch ожидает driver 12.6+, а есть 12.5

**Решение:** Варианты:
- Обновить драйвер NVIDIA до версии с поддержкой CUDA 12.6+
- Использовать PyTorch 2.0.1 cu118 (требует CUDA 11.8 драйвер)
- Использовать CPU mode (автоматически fallback)

---

## Полезные команды для диагностики:

```bash
# Проверить версию CUDA драйвера
nvidia-smi | grep CUDA

# Проверить Docker volumes (модели)
docker volume ls
docker volume inspect docker3_pyannote-models

# Очистить Docker кэш и пересобрать
docker compose -f docker3/docker-compose.pyannote.yml down -v
docker compose -f docker3/docker-compose.pyannote.yml up -d --build --no-cache
```












Edit Dockerfile.pyannote
Removed 14 lines
Теперь подход:

Шаг 1: pip сам устанавливает pyannote.audio со ВСЕМИ зависимостями (не нужно угадывать)
Шаг 2: Переписываем torch на 2.5.1+cu124 поверх того что pip поставил
Риск: на шаге 1 может снова быть ошибка с хешами nvidia-cufft (как раньше). Если будет — скажи.

Запускай:


HF_TOKEN=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 docker compose -f docker3/docker-compose.pyannote.yml build --no-cache && \
HF_TOKEN=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 docker compose -f docker3/docker-compose.pyannote.yml up -d
Dockerfile.pyannote
day curl komadu dlay proverki

curl http://localhost:8400/health
Если работает, должно вернуть что-то типа:


{"status": "ok", "service": "pyannote-diarization", "model": "pyannote/speaker-diarization-community-1", "gpu_available": true}
Ключевое — gpu_available: true.

sozdaya whatwe_did.md napisi sto mis delali sto realizovali kakuyu problemi reshili shaq za shaqom kak reshili vse sto u tebya v contekstnom okne napisi tuda dvay!!!
Failed to authenticate. API Error: 401 Invalid bearer token

No response requested.

settings.json
do it
Failed to authenticate. API Error: 401 Invalid bearer token