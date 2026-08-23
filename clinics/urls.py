from rest_framework.routers import DefaultRouter

from .views import AppointmentViewSet, ClinicViewSet, DoctorViewSet, ServiceViewSet

router = DefaultRouter()
router.register('clinics', ClinicViewSet, basename='clinic')
router.register('services', ServiceViewSet, basename='service')
router.register('doctors', DoctorViewSet, basename='doctor')
router.register('appointments', AppointmentViewSet, basename='appointment')

urlpatterns = router.urls
