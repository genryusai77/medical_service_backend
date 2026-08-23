from django.db import IntegrityError
from django.utils import timezone
from rest_framework import serializers

from .models import Appointment, Clinic, Doctor, Service


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['id', 'clinic', 'name', 'description', 'price']


class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = ['id', 'clinic', 'services', 'full_name', 'specialization', 'experience_years', 'photo']


class ClinicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clinic
        fields = ['id', 'name', 'city', 'address', 'phone', 'description', 'working_hours']


class ClinicDetailSerializer(ClinicSerializer):
    services = ServiceSerializer(many=True, read_only=True)
    doctors = DoctorSerializer(many=True, read_only=True)

    class Meta(ClinicSerializer.Meta):
        fields = ClinicSerializer.Meta.fields + ['services', 'doctors']


class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = [
            'id', 'clinic', 'doctor', 'service', 'patient_name', 'patient_phone',
            'preferred_date', 'preferred_time', 'comment', 'status', 'created_at',
        ]
        read_only_fields = ['status', 'created_at']
        # Disable DRF's auto-generated UniqueTogetherValidator for the
        # clinics_appt_slot_uniq constraint: the same check is already done
        # below via Appointment.get_conflicting_appointments (the single
        # source of truth shared with Appointment.clean()), and letting both
        # run would surface two separate error messages for one conflict.
        validators = []

    def validate(self, attrs):
        clinic = attrs.get('clinic', getattr(self.instance, 'clinic', None))
        doctor = attrs.get('doctor', getattr(self.instance, 'doctor', None))
        service = attrs.get('service', getattr(self.instance, 'service', None))
        preferred_date = attrs.get('preferred_date', getattr(self.instance, 'preferred_date', None))
        preferred_time = attrs.get('preferred_time', getattr(self.instance, 'preferred_time', None))

        if doctor and clinic and doctor.clinic_id != clinic.id:
            raise serializers.ValidationError({'doctor': 'Doctor does not belong to the selected clinic.'})
        if service and clinic and service.clinic_id != clinic.id:
            raise serializers.ValidationError({'service': 'Service does not belong to the selected clinic.'})

        if preferred_date and preferred_date < timezone.localdate():
            raise serializers.ValidationError({'preferred_date': 'Preferred date cannot be in the past.'})

        if (
            preferred_date and preferred_time
            and preferred_date == timezone.localdate()
            and preferred_time < timezone.localtime().time()
        ):
            raise serializers.ValidationError({'preferred_time': 'Preferred time cannot be in the past.'})

        if doctor and preferred_date and preferred_time:
            conflicts = Appointment.get_conflicting_appointments(
                doctor=doctor,
                preferred_date=preferred_date,
                preferred_time=preferred_time,
                exclude_pk=self.instance.pk if self.instance is not None else None,
            )
            if conflicts.exists():
                raise serializers.ValidationError(
                    {'doctor': 'Doctor already has an appointment at this date and time.'}
                )

        return attrs

    def create(self, validated_data):
        # Safety net for the race window between validate() and the INSERT:
        # if two requests for the same slot pass validation concurrently,
        # the DB-level clinics_appt_slot_uniq constraint (see models.py)
        # rejects the second write with an IntegrityError. Surface that as a
        # normal 400 validation error instead of letting it bubble up as an
        # unhandled 500.
        try:
            return super().create(validated_data)
        except IntegrityError:
            raise serializers.ValidationError(
                {'doctor': 'Doctor already has an appointment at this date and time.'}
            )
