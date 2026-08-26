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

- `OPENAI_API_KEY` — обязателен, иначе не работает `/api/assistant/chat/`.
- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` — пока не подключены к `.env` (захардкожены в `settings.py`).

## Тесты

```bash
.venv/bin/python manage.py test clinics
```

## Документация API

- Swagger: `http://localhost:8000/api/docs/`
- Redoc: `http://localhost:8000/api/redoc/`
