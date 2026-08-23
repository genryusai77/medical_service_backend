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

    def validate(self, attrs):
        clinic = attrs.get('clinic')
        doctor = attrs.get('doctor')
        service = attrs.get('service')
        if doctor and doctor.clinic_id != clinic.id:
            raise serializers.ValidationError({'doctor': 'Doctor does not belong to the selected clinic.'})
        if service and service.clinic_id != clinic.id:
            raise serializers.ValidationError({'service': 'Service does not belong to the selected clinic.'})
        return attrs
