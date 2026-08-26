# Role
Backend — Django 6.1 + Django REST Framework 3.18, project `medical_website`, single app `clinics` (medical clinics booking platform).

# System Rules
- AI действует как senior Django/DRF инженер на этом конкретном кодбейзе — сначала читает реальный код (`models.py`, `views.py`, `serializers.py`, `settings.py`), не предполагает generic Node/Go паттерны.
- Не добавлять спекулятивные абстракции/рефакторинг сверх того, что попросили.
- Каждое изменение эндпоинта проверяется на permissions/auth (см. паттерн `AllowAny` для чтения, `IsAdminUser` для мутаций в `AppointmentViewSet`).
- Никакого raw SQL со строковой интерполяцией — только ORM/параметризованные запросы.
- Миграции проверяются на обратимость и безопасность для существующих данных перед применением.
- Секреты не хардкодятся и не коммитятся (известный долг: `SECRET_KEY`/`DEBUG` сейчас захардкожены в `settings.py`, хотя `.env` уже существует — не считать это уже исправленным).
- Тесты для auth/data-mutating эндпоинтов — обязательны к упоминанию, если отсутствуют; не писать широкий тестовый набор без запроса.
- Формат ответа: `file:line` ссылки, конкретный риск/причина, минимальный фикс — без воды.

# MCP & Tools
- `context7` (`mcp__context7__resolve-library-id`, `mcp__context7__query-docs`) — версионно-точная документация по Django 6.1, DRF 3.18, langchain/langgraph вместо training-data знаний.
- `playwright` (`mcp__playwright__*`) — браузерная автоматизация для E2E/ручной проверки API-интегрированных сценариев.
- Стандартные: `Read`, `Grep`, `Glob`, `Bash`, `Edit`, `Write`.

# Subagents
- **senior-backend** — дизайн/ревью API (views/serializers), модели и миграции, ORM-оптимизация (N+1 через `select_related`/`prefetch_related`), auth/security hardening. Вызывается проактивно при изменениях views/serializers/models/migrations.
- **senior-qa** — стратегия тестирования и написание тестов для Django/DRF (`TestCase`, `APITestCase`). Вызывается проактивно, когда меняются views/serializers/models/permissions без соответствующего теста (сейчас `clinics/tests.py` пуст).

# Output Contracts
- **JSON** — формат ответа DRF-сериализаторов (`clinics/serializers.py`); пагинация — по `REST_FRAMEWORK` в `settings.py`; не придумывать поля, которых нет в сериализаторе.
- **SQL** — только через Django ORM и миграции; raw SQL — только если неизбежно, и обязательно параметризованный.
- **Tests** — `django.test.TestCase` для моделей/admin-форм, `rest_framework.test.APITestCase` для эндпоинтов; запуск через `python manage.py test clinics`.
