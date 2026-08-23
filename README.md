# Medical Clinics API

Django + DRF backend for browsing clinics/services/doctors and booking appointments.

## Running locally

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py runserver
```

API is mounted at `/api/`, admin at `/admin/`.

`.env.example` documents the expected environment variables, but note `medical_website/settings.py` currently hardcodes `SECRET_KEY`/`DEBUG`/`ALLOWED_HOSTS` inline rather than reading `.env` — editing `.env` has no effect yet until that's wired up (e.g. via `python-decouple`).

## API docs (for frontend integration)

The API schema is auto-generated from the DRF viewsets/serializers via `drf-spectacular`, so it always matches the current code:

- Swagger UI (interactive, try-it-out): `http://localhost:8000/api/docs/`
- Redoc (read-only, nicer for browsing): `http://localhost:8000/api/redoc/`
- Raw OpenAPI schema (YAML): `http://localhost:8000/api/schema/`

### Generating a typed API client for React

Rather than hand-writing `fetch` calls and response types, generate them from the OpenAPI schema:

```bash
# TypeScript types only
npx openapi-typescript http://localhost:8000/api/schema/ -o src/api/schema.d.ts

# or a full typed client + React Query hooks
npx orval --input http://localhost:8000/api/schema/ --output src/api/client.ts
```

Re-run the generator whenever the backend API changes (new fields, new endpoints, etc.) to keep frontend types in sync automatically instead of manually updating interfaces.

### CORS

`django-cors-headers` is configured to allow requests from local React dev servers:
`http://localhost:3000`, `http://127.0.0.1:3000` (Create React App) and `http://localhost:5173`, `http://127.0.0.1:5173` (Vite). If the frontend runs on a different origin, add it to `CORS_ALLOWED_ORIGINS` in `medical_website/settings.py`.

### Auth notes

- Clinic/Service/Doctor list & retrieve endpoints and appointment creation (`POST /api/appointments/`) are public, no auth required.
- Listing/retrieving/confirming/cancelling appointments requires an admin (staff) user — done via Django admin at `/admin/`, not through the API.
