# Medical Clinics API

Django + DRF бэкенд: клиники, услуги, врачи, запись на приём. Плюс AI-ассистент для записи (LangChain + OpenAI).

## Запуск

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py runserver
```

API: `/api/`, админка: `/admin/`.

## Переменные окружения

Скопируй `.env.example` в `.env`:

- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` — читаются через `django-environ`; без `.env` используются dev-значения по умолчанию.
- `DATABASE_URL` — строка подключения к Postgres (`postgres://user:pass@host:5432/db`); не задавай (не оставляй пустой строкой) для локальной разработки на SQLite.
- `CORS_ALLOWED_ORIGINS` — список origin'ов фронтенда через запятую; не задавай для локальных дефолтов (`localhost:3000`/`5173`).
- `OPENAI_API_KEY` — обязателен, иначе не работает `/api/assistant/chat/`.

## Тесты

```bash
.venv/bin/python manage.py test clinics
```

## Документация API

- Swagger: `http://localhost:8000/api/docs/`
- Redoc: `http://localhost:8000/api/redoc/`

## Деплой на Railway

1. Создай проект на [railway.app](https://railway.app) из этого репозитория и добавь сервис Postgres (Railway сам создаст `DATABASE_URL` и подставит его в переменные окружения web-сервиса).
2. В настройках web-сервиса задай переменные окружения (см. `.env.example`):
   - `SECRET_KEY` — сгенерируй отдельное значение для прод (не используй dev-дефолт из `settings.py`).
   - `DEBUG=False`
   - `ALLOWED_HOSTS` — домен Railway-сервиса (например `myapp.up.railway.app`); домен из `RAILWAY_PUBLIC_DOMAIN` подхватывается автоматически, но переменную всё равно стоит задать явно.
   - `CORS_ALLOWED_ORIGINS` — домен прод-фронтенда.
   - `OPENAI_API_KEY` — если нужен AI-ассистент.
3. `Procfile` при каждом деплое сначала прогоняет `migrate` и `collectstatic`, затем стартует `gunicorn` (у Railway нет отдельной release-фазы как у Heroku, поэтому это сделано одной командой `web`).
4. Статика отдаётся через `whitenoise` (настроено в `MIDDLEWARE`/`STORAGES`), отдельный сервер для статики не нужен.
5. **Медиа-файлы (`Doctor.photo`) не персистентны на Railway** — файловая система эфемерна и очищается при каждом редеплое. Для продакшена нужно внешнее хранилище (например S3-совместимое через `django-storages`); сейчас это не настроено.
