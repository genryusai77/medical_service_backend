from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAdminUser

from .models import Appointment, Clinic, Doctor, Service
from .serializers import (
    AppointmentSerializer,
    ClinicDetailSerializer,
    ClinicSerializer,
    DoctorSerializer,
    ServiceSerializer,
)


def _parse_id_param(value, field_name):
    """
    Validate a query-param that's meant to be used as a numeric FK/M2M id
    filter (e.g. ?clinic=1). Returns None if `value` is falsy (param not
    supplied), otherwise the parsed int. Raises a DRF ValidationError (400)
    for anything that isn't a valid non-negative integer, instead of letting
    a bad value reach `.filter(...)` and blow up with an unhandled 500.
    """
    if not value:
        return None
    if not value.isdigit():
        raise ValidationError({field_name: f'"{value}" is not a valid integer.'})
    return int(value)


class ClinicViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Clinic.objects.all()
    permission_classes = [AllowAny]

    def get_queryset(self):
        if self.action == 'retrieve':
            # ClinicDetailSerializer nests services (reverse FK) and doctors,
            # and each doctor is further serialized with its M2M `services`.
            # Without these hints, rendering a single clinic still issues one
            # extra query per doctor for `doctor.services.all()` (N+1).
            return Clinic.objects.prefetch_related('services', 'doctors__services')
        return Clinic.objects.all()

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ClinicDetailSerializer
        return ClinicSerializer


class ServiceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Service.objects.select_related('clinic').all()
    serializer_class = ServiceSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        clinic_id = _parse_id_param(self.request.query_params.get('clinic'), 'clinic')
        if clinic_id is not None:
            queryset = queryset.filter(clinic_id=clinic_id)
        return queryset


class DoctorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Doctor.objects.select_related('clinic').prefetch_related('services').all()
    serializer_class = DoctorSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        clinic_id = _parse_id_param(self.request.query_params.get('clinic'), 'clinic')
        service_id = _parse_id_param(self.request.query_params.get('service'), 'service')
        if clinic_id is not None:
            queryset = queryset.filter(clinic_id=clinic_id)
        if service_id is not None:
            queryset = queryset.filter(services__id=service_id)
        return queryset


class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.select_related('clinic', 'doctor', 'service').all()
    serializer_class = AppointmentSerializer
    http_method_names = ['get', 'post', 'head', 'options']

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return [IsAdminUser()]
