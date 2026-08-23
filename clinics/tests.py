import datetime

from django import forms
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Appointment, Clinic, Doctor, Service


def _appointment_admin_form_class():
    """
    Mirror clinics.admin.AppointmentAdmin, which registers Appointment with
    no custom form, so the default ModelForm (as Django admin would build
    it) is what actually runs in production.
    """
    return forms.modelform_factory(Appointment, fields='__all__')


class AppointmentModelCleanTests(TestCase):
    """Fix #1: Appointment.clean() is the shared double-booking check."""

    def setUp(self):
        self.clinic = Clinic.objects.create(name='Clinic', city='City', address='Addr', phone='123')
        self.doctor = Doctor.objects.create(clinic=self.clinic, full_name='Dr. House', specialization='GP')
        self.tomorrow = timezone.localdate() + datetime.timedelta(days=1)
        self.existing = Appointment.objects.create(
            clinic=self.clinic,
            doctor=self.doctor,
            patient_name='Alice',
            patient_phone='111',
            preferred_date=self.tomorrow,
            preferred_time=datetime.time(10, 0),
        )

    def test_clean_rejects_conflicting_slot(self):
        conflicting = Appointment(
            clinic=self.clinic,
            doctor=self.doctor,
            patient_name='Bob',
            patient_phone='222',
            preferred_date=self.tomorrow,
            preferred_time=datetime.time(10, 0),
        )
        with self.assertRaises(DjangoValidationError):
            conflicting.clean()

    def test_clean_ignores_cancelled_conflicts(self):
        self.existing.status = Appointment.Status.CANCELLED
        self.existing.save()
        new_appt = Appointment(
            clinic=self.clinic,
            doctor=self.doctor,
            patient_name='Bob',
            patient_phone='222',
            preferred_date=self.tomorrow,
            preferred_time=datetime.time(10, 0),
        )
        new_appt.clean()  # should not raise

    def test_clean_excludes_self_on_update(self):
        self.existing.comment = 'updated'
        self.existing.clean()  # should not conflict with itself


class AppointmentAdminFormDoubleBookingTests(TestCase):
    """
    Fix #1: the default admin ModelForm (no custom AppointmentAdminForm
    exists) must reject a double-booking, because it runs full_clean()
    (and therefore Appointment.clean()) via ModelForm._post_clean().
    """

    def setUp(self):
        self.clinic = Clinic.objects.create(name='Clinic', city='City', address='Addr', phone='123')
        self.doctor = Doctor.objects.create(clinic=self.clinic, full_name='Dr. House', specialization='GP')
        self.tomorrow = timezone.localdate() + datetime.timedelta(days=1)
        Appointment.objects.create(
            clinic=self.clinic,
            doctor=self.doctor,
            patient_name='Alice',
            patient_phone='111',
            preferred_date=self.tomorrow,
            preferred_time=datetime.time(10, 0),
        )

    def _form_data(self, **overrides):
        data = {
            'clinic': self.clinic.pk,
            'doctor': self.doctor.pk,
            'service': '',
            'patient_name': 'Bob',
            'patient_phone': '222',
            'preferred_date': self.tomorrow.isoformat(),
            'preferred_time': '10:00',
            'comment': '',
            'status': Appointment.Status.PENDING,
        }
        data.update(overrides)
        return data

    def test_admin_form_rejects_double_booking(self):
        FormClass = _appointment_admin_form_class()
        form = FormClass(data=self._form_data())
        self.assertFalse(form.is_valid())
        self.assertIn('doctor', form.errors)

    def test_admin_form_does_not_show_duplicate_error(self):
        # Regression guard: clean()'s friendly message and the DB
        # UniqueConstraint shouldn't both surface for the same conflict.
        FormClass = _appointment_admin_form_class()
        form = FormClass(data=self._form_data())
        self.assertFalse(form.is_valid())
        all_messages = [msg for messages in form.errors.values() for msg in messages]
        conflict_messages = [m for m in all_messages if 'already' in m.lower()]
        self.assertEqual(len(conflict_messages), 1, form.errors)

    def test_admin_form_accepts_non_conflicting_slot(self):
        FormClass = _appointment_admin_form_class()
        form = FormClass(data=self._form_data(preferred_time='11:00'))
        self.assertTrue(form.is_valid(), form.errors)


class AppointmentDbConstraintTests(TestCase):
    """Fix #2: DB-level partial UniqueConstraint as a race-condition backstop."""

    def setUp(self):
        self.clinic = Clinic.objects.create(name='Clinic', city='City', address='Addr', phone='123')
        self.doctor = Doctor.objects.create(clinic=self.clinic, full_name='Dr. House', specialization='GP')
        self.tomorrow = timezone.localdate() + datetime.timedelta(days=1)

    def test_bulk_create_bypassing_python_validation_hits_db_constraint(self):
        # .objects.create()/bulk_create() skip clean()/full_clean() entirely,
        # simulating two requests racing past the application-level check.
        Appointment.objects.create(
            clinic=self.clinic,
            doctor=self.doctor,
            patient_name='Alice',
            patient_phone='111',
            preferred_date=self.tomorrow,
            preferred_time=datetime.time(10, 0),
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Appointment.objects.create(
                    clinic=self.clinic,
                    doctor=self.doctor,
                    patient_name='Bob',
                    patient_phone='222',
                    preferred_date=self.tomorrow,
                    preferred_time=datetime.time(10, 0),
                )

    def test_cancelled_appointment_frees_up_the_slot_at_db_level(self):
        cancelled = Appointment.objects.create(
            clinic=self.clinic,
            doctor=self.doctor,
            patient_name='Alice',
            patient_phone='111',
            preferred_date=self.tomorrow,
            preferred_time=datetime.time(10, 0),
            status=Appointment.Status.CANCELLED,
        )
        # Should not raise: the partial unique index excludes cancelled rows.
        Appointment.objects.create(
            clinic=self.clinic,
            doctor=self.doctor,
            patient_name='Bob',
            patient_phone='222',
            preferred_date=self.tomorrow,
            preferred_time=datetime.time(10, 0),
        )
        self.assertTrue(Appointment.objects.filter(pk=cancelled.pk).exists())


class AppointmentApiTests(TestCase):
    """API-level coverage for fixes #1, #2 and #4."""

    def setUp(self):
        self.client = APIClient()
        self.clinic = Clinic.objects.create(name='Clinic', city='City', address='Addr', phone='123')
        self.doctor = Doctor.objects.create(clinic=self.clinic, full_name='Dr. House', specialization='GP')
        self.tomorrow = timezone.localdate() + datetime.timedelta(days=1)

    def _payload(self, **overrides):
        data = {
            'clinic': self.clinic.pk,
            'doctor': self.doctor.pk,
            'patient_name': 'Alice',
            'patient_phone': '111',
            'preferred_date': self.tomorrow.isoformat(),
            'preferred_time': '10:00:00',
        }
        data.update(overrides)
        return data

    def test_create_then_double_booking_rejected_with_400(self):
        first = self.client.post('/api/appointments/', self._payload(), format='json')
        self.assertEqual(first.status_code, 201, first.data)

        second = self.client.post('/api/appointments/', self._payload(patient_name='Bob'), format='json')
        self.assertEqual(second.status_code, 400)
        self.assertIn('doctor', second.data)

    def test_race_past_python_validation_is_handled_gracefully_via_create(self):
        # Directly exercise the serializer's create()/IntegrityError handling
        # by writing a conflicting row after validate() would have run.
        from rest_framework.exceptions import ValidationError as DRFValidationError

        from .serializers import AppointmentSerializer

        Appointment.objects.create(
            clinic=self.clinic,
            doctor=self.doctor,
            patient_name='Alice',
            patient_phone='111',
            preferred_date=self.tomorrow,
            preferred_time=datetime.time(10, 0),
        )
        serializer = AppointmentSerializer()
        with self.assertRaises(DRFValidationError):
            serializer.create({
                'clinic': self.clinic,
                'doctor': self.doctor,
                'patient_name': 'Bob',
                'patient_phone': '222',
                'preferred_date': self.tomorrow,
                'preferred_time': datetime.time(10, 0),
            })

    def test_same_day_past_time_rejected(self):
        past_time = (timezone.localtime() - datetime.timedelta(hours=1)).time()
        response = self.client.post(
            '/api/appointments/',
            self._payload(preferred_date=timezone.localdate().isoformat(), preferred_time=past_time.isoformat()),
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('preferred_time', response.data)

    def test_same_day_future_time_accepted(self):
        future_time = (timezone.localtime() + datetime.timedelta(hours=1)).time()
        response = self.client.post(
            '/api/appointments/',
            self._payload(preferred_date=timezone.localdate().isoformat(), preferred_time=future_time.isoformat()),
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.data)


class FilterQueryParamTests(TestCase):
    """Fix #3: non-integer ?clinic=/?service= params return 400, not 500."""

    def setUp(self):
        self.client = APIClient()
        self.clinic = Clinic.objects.create(name='Clinic', city='City', address='Addr', phone='123')
        Service.objects.create(clinic=self.clinic, name='Checkup', price='10.00')

    def test_services_bad_clinic_param_returns_400(self):
        response = self.client.get('/api/services/', {'clinic': 'not-a-number'})
        self.assertEqual(response.status_code, 400)

    def test_services_valid_clinic_param_returns_200(self):
        response = self.client.get('/api/services/', {'clinic': str(self.clinic.pk)})
        self.assertEqual(response.status_code, 200)

    def test_doctors_bad_clinic_param_returns_400(self):
        response = self.client.get('/api/doctors/', {'clinic': 'abc'})
        self.assertEqual(response.status_code, 400)

    def test_doctors_bad_service_param_returns_400(self):
        response = self.client.get('/api/doctors/', {'service': 'abc'})
        self.assertEqual(response.status_code, 400)

    def test_doctors_valid_params_return_200(self):
        response = self.client.get('/api/doctors/', {'clinic': str(self.clinic.pk), 'service': '1'})
        self.assertEqual(response.status_code, 200)
