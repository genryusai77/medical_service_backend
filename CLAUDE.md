# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Django + Django REST Framework backend (`medical_website` project) for a medical clinics platform. A single app, `clinics`, exposes a read-only public API for browsing clinics/services/doctors and a create-only public endpoint for booking appointments; mutation of appointments (confirm/cancel) is admin-only.

## Commands

Activate the existing virtualenv at `.venv/` before running Python/Django commands (or prefix with `.venv/bin/python`).

```bash
# Run the dev server
python manage.py runserver

# Migrations
python manage.py makemigrations
python manage.py migrate

# Tests (currently no tests are implemented in clinics/tests.py)
python manage.py test
python manage.py test clinics                    # single app
python manage.py test clinics.tests.SomeTestCase  # single test case, once written

# Django shell / superuser
python manage.py shell
python manage.py createsuperuser
```

There is no linter/formatter configured in this repo (no `pyproject.toml`, `setup.cfg`, or CI config present) — don't assume one.

## Architecture

- **Single Django project, single app.** `medical_website/` holds project-level settings/urls/wsgi/asgi; all domain logic lives in `clinics/`. Routes are mounted at `/api/` (DRF router) and `/admin/` (Django admin) — see `medical_website/urls.py`.
- **Models** (`clinics/models.py`): `Clinic` → `Service` (FK) and `Doctor` (FK), with `Doctor.services` as an M2M that is expected to be a subset of the doctor's own clinic's services (enforced in `DoctorAdminForm.clean`, **not** at the serializer/model level). `Appointment` FKs to `Clinic`/`Doctor`/`Service` and carries its own `status` state machine (`pending`/`confirmed`/`cancelled`).
- **Double-booking prevention**: `AppointmentSerializer.validate` (`clinics/serializers.py`) rejects a new/updated appointment if the same doctor already has a non-cancelled appointment at the same `preferred_date`/`preferred_time`. This is backed by the `clinics_appt_slot_idx` index on `Appointment(doctor, preferred_date, preferred_time)` (see the migration and the model's `Meta.indexes` comment) — keep the index and the validation logic in sync if either changes.
- **Serializers layer**: `ClinicDetailSerializer` (used only on `retrieve`) nests `services` and `doctors` and is paired with `ClinicViewSet.get_queryset` using `prefetch_related('services', 'doctors__services')` specifically to avoid N+1 queries from the nested doctor→services M2M — when adding new nested fields, extend the `prefetch_related` list to match.
- **Permissions pattern** (`clinics/views.py`): `Clinic`/`Service`/`Doctor` viewsets are `ReadOnlyModelViewSet` + `AllowAny` (public browsing). `AppointmentViewSet` restricts `http_method_names` to `get/post/head/options` (no update/delete via API — status changes happen through the admin) and uses `get_permissions()` to allow anonymous `create` while requiring `IsAdminUser` for everything else (list/retrieve).
- **Query filtering convention**: `ServiceViewSet`/`DoctorViewSet` filter via `?clinic=<id>` (and `?service=<id>` for doctors) query params in `get_queryset`, not via `django-filter` — follow this pattern for new filterable list endpoints rather than introducing a filtering library.
- **Admin** (`clinics/admin.py`): `DoctorAdminForm` cross-validates that assigned `services` belong to the doctor's `clinic`; mirror this constraint if it's ever moved into the serializer.
- **Settings**: SQLite in dev (`db.sqlite3`), `DEBUG=True`, secret key hardcoded — this is a "quick-start" config, not production-ready. An `.env` file exists with `SECRET_KEY`/`DEBUG`/`ALLOWED_HOSTS` keys but `medical_website/settings.py` does not currently read from it (values are hardcoded inline); wire up `python-decouple`/`django-environ`/etc. if asked to make settings env-driven rather than assuming it's already done.
- **Media**: `Doctor.photo` uploads go to `MEDIA_ROOT/doctors/`; media is only served via Django in `DEBUG` mode (`medical_website/urls.py`).
