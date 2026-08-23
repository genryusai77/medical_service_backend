from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class Clinic(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')
    city = models.CharField(max_length=100, verbose_name='Город')
    address = models.CharField(max_length=255, verbose_name='Адрес')
    phone = models.CharField(max_length=32, verbose_name='Телефон')
    description = models.TextField(blank=True, verbose_name='Описание')
    working_hours = models.CharField(max_length=255, blank=True, verbose_name='Часы работы')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        ordering = ['name']
        verbose_name = 'Клиника'
        verbose_name_plural = 'Клиники'

    def __str__(self):
        return self.name


class Service(models.Model):
    clinic = models.ForeignKey(
        Clinic, on_delete=models.CASCADE, related_name='services', verbose_name='Клиника'
    )
    name = models.CharField(max_length=255, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], verbose_name='Цена'
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Услуга'
        verbose_name_plural = 'Услуги'

    def __str__(self):
        return f'{self.name} ({self.clinic.name})'


class Doctor(models.Model):
    clinic = models.ForeignKey(
        Clinic, on_delete=models.CASCADE, related_name='doctors', verbose_name='Клиника'
    )
    services = models.ManyToManyField(
        Service, related_name='doctors', blank=True, verbose_name='Услуги'
    )
    full_name = models.CharField(max_length=255, verbose_name='ФИО')
    specialization = models.CharField(max_length=255, verbose_name='Специализация')
    experience_years = models.PositiveSmallIntegerField(default=0, verbose_name='Стаж (лет)')
    photo = models.ImageField(upload_to='doctors/', blank=True, null=True, verbose_name='Фото')

    class Meta:
        ordering = ['full_name']
        verbose_name = 'Врач'
        verbose_name_plural = 'Врачи'

    def __str__(self):
        return f'{self.full_name} ({self.specialization})'


class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Ожидает подтверждения'
        CONFIRMED = 'confirmed', 'Подтверждена'
        CANCELLED = 'cancelled', 'Отменена'

    clinic = models.ForeignKey(
        Clinic, on_delete=models.CASCADE, related_name='appointments', verbose_name='Клиника'
    )
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.SET_NULL,
        related_name='appointments',
        null=True,
        blank=True,
        verbose_name='Врач',
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        related_name='appointments',
        null=True,
        blank=True,
        verbose_name='Услуга',
    )
    patient_name = models.CharField(max_length=255, verbose_name='ФИО пациента')
    patient_phone = models.CharField(max_length=32, verbose_name='Телефон пациента')
    preferred_date = models.DateField(verbose_name='Желаемая дата')
    preferred_time = models.TimeField(verbose_name='Желаемое время')
    comment = models.TextField(blank=True, verbose_name='Комментарий')
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING, verbose_name='Статус'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    # Fields that make up the doctor/date/time "slot" uniqueness rule. Shared
    # between the DB constraint, clean(), and validate_constraints() below so
    # they can't drift out of sync.
    SLOT_FIELDS = ('doctor', 'preferred_date', 'preferred_time')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Запись на приём'
        verbose_name_plural = 'Записи на приём'
        indexes = [
            # Matches admin list_filter on status.
            models.Index(fields=['status'], name='clinics_appt_status_idx'),
        ]
        constraints = [
            # DB-level enforcement of the double-booking rule (last line of
            # defense against concurrent requests racing past the
            # application-level check in clean()/AppointmentSerializer).
            # Cancelled appointments free up the slot, so they're excluded.
            models.UniqueConstraint(
                fields=['doctor', 'preferred_date', 'preferred_time'],
                # NB: Meta's class body isn't in Appointment's scope, so this
                # can't reference Status.CANCELLED directly; kept in sync
                # with Appointment.Status.CANCELLED = 'cancelled'.
                condition=~Q(status='cancelled'),
                name='clinics_appt_slot_uniq',
            ),
        ]

    def __str__(self):
        return f'{self.patient_name} -> {self.clinic.name} ({self.preferred_date})'

    @classmethod
    def get_conflicting_appointments(cls, *, doctor, preferred_date, preferred_time, exclude_pk=None):
        """
        Return the queryset of non-cancelled appointments already occupying
        the given doctor/date/time slot. This is the single source of truth
        for the double-booking check, used by both clean() (so it's enforced
        via full_clean(), which Django admin's ModelForm.save() triggers) and
        AppointmentSerializer.validate() (so the public API gets the same
        friendly, pre-save error instead of relying solely on the DB
        constraint).
        """
        if not (doctor and preferred_date and preferred_time):
            return cls.objects.none()
        conflicts = cls.objects.filter(
            doctor=doctor,
            preferred_date=preferred_date,
            preferred_time=preferred_time,
        ).exclude(status=cls.Status.CANCELLED)
        if exclude_pk is not None:
            conflicts = conflicts.exclude(pk=exclude_pk)
        return conflicts

    def clean(self):
        super().clean()
        if self.doctor_id and self.preferred_date and self.preferred_time:
            conflicts = self.get_conflicting_appointments(
                doctor=self.doctor_id,
                preferred_date=self.preferred_date,
                preferred_time=self.preferred_time,
                exclude_pk=self.pk,
            )
            if conflicts.exists():
                raise ValidationError(
                    {'doctor': 'Doctor already has an appointment at this date and time.'}
                )

    def validate_constraints(self, exclude=None):
        # The clinics_appt_slot_uniq constraint duplicates the check already
        # performed (with a friendlier, field-specific message) by clean()
        # above, which full_clean() always runs before validate_constraints().
        # Without this override, admin forms would show two separate error
        # messages for the same conflict (clean()'s, plus a generic
        # "Appointment with this Doctor, Preferred date and Preferred time
        # already exists." from the constraint). Skip re-checking it here;
        # the constraint itself is kept at the DB level as a race-condition
        # safety net (see AppointmentSerializer.create()).
        exclude = set(exclude or []) | set(self.SLOT_FIELDS)
        super().validate_constraints(exclude=exclude)
