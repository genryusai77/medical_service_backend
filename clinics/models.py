from django.core.validators import MinValueValidator
from django.db import models


class Clinic(models.Model):
    name = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    phone = models.CharField(max_length=32)
    description = models.TextField(blank=True)
    working_hours = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Service(models.Model):
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='services')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.clinic.name})'


class Doctor(models.Model):
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='doctors')
    services = models.ManyToManyField(Service, related_name='doctors', blank=True)
    full_name = models.CharField(max_length=255)
    specialization = models.CharField(max_length=255)
    experience_years = models.PositiveSmallIntegerField(default=0)
    photo = models.ImageField(upload_to='doctors/', blank=True, null=True)

    class Meta:
        ordering = ['full_name']

    def __str__(self):
        return f'{self.full_name} ({self.specialization})'


class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        CANCELLED = 'cancelled', 'Cancelled'

    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, related_name='appointments', null=True, blank=True)
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, related_name='appointments', null=True, blank=True)
    patient_name = models.CharField(max_length=255)
    patient_phone = models.CharField(max_length=32)
    preferred_date = models.DateField()
    preferred_time = models.TimeField()
    comment = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.patient_name} -> {self.clinic.name} ({self.preferred_date})'
