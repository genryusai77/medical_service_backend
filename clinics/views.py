from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAdminUser

from .models import Appointment, Clinic, Doctor, Service
from .serializers import (
    AppointmentSerializer,
    ClinicDetailSerializer,
    ClinicSerializer,
    DoctorSerializer,
    ServiceSerializer,
)


class ClinicViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Clinic.objects.all()
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ClinicDetailSerializer
        return ClinicSerializer


class ServiceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Service.objects.select_related('clinic').all()
    serializer_class = ServiceSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['clinic']

    def get_queryset(self):
        queryset = super().get_queryset()
        clinic_id = self.request.query_params.get('clinic')
        if clinic_id:
            queryset = queryset.filter(clinic_id=clinic_id)
        return queryset


class DoctorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Doctor.objects.select_related('clinic').prefetch_related('services').all()
    serializer_class = DoctorSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        clinic_id = self.request.query_params.get('clinic')
        service_id = self.request.query_params.get('service')
        if clinic_id:
            queryset = queryset.filter(clinic_id=clinic_id)
        if service_id:
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
