from django.contrib import admin

from .models import Appointment, Clinic, Doctor, Service


@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'phone', 'created_at']
    list_filter = ['city']
    search_fields = ['name', 'city', 'address']


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'clinic', 'price']
    list_filter = ['clinic']
    search_fields = ['name', 'clinic__name']


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'specialization', 'clinic', 'experience_years']
    list_filter = ['clinic', 'specialization']
    search_fields = ['full_name', 'specialization']
    filter_horizontal = ['services']


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['patient_name', 'clinic', 'doctor', 'service', 'preferred_date', 'preferred_time', 'status', 'created_at']
    list_filter = ['status', 'clinic', 'preferred_date']
    search_fields = ['patient_name', 'patient_phone']
    date_hierarchy = 'preferred_date'
