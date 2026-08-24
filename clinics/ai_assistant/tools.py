from langchain_core.tools import tool

from clinics.models import Clinic, Service
from clinics.serializers import AppointmentSerializer


@tool
def search_clinics(query: str = '', city: str = '') -> list[dict]:
    """Search clinics by name and/or city."""
    qs = Clinic.objects.all()
    if city:
        qs = qs.filter(city__icontains=city)
    if query:
        qs = qs.filter(name__icontains=query)
    return [
        {
            'id': c.id,
            'name': c.name,
            'city': c.city,
            'address': c.address,
            'phone': c.phone,
            'working_hours': c.working_hours,
        }
        for c in qs[:10]
    ]


@tool
def search_services(query: str = '', clinic_id: int | None = None) -> list[dict]:
    """Search services by name and/or clinic id."""
    qs = Service.objects.select_related('clinic').all()
    if clinic_id:
        qs = qs.filter(clinic_id=clinic_id)
    if query:
        qs = qs.filter(name__icontains=query)
    return [
        {
            'id': s.id,
            'name': s.name,
            'price': str(s.price),
            'clinic_id': s.clinic_id,
            'clinic_name': s.clinic.name,
        }
        for s in qs[:10]
    ]


@tool
def book_appointment(
    clinic_id: int,
    patient_name: str,
    patient_phone: str,
    preferred_date: str,
    preferred_time: str,
    doctor_id: int | None = None,
    service_id: int | None = None,
    comment: str = '',
) -> dict:
    """Book an appointment at a clinic for a patient.

    preferred_date must be formatted YYYY-MM-DD and preferred_time as HH:MM.
    Only use clinic_id/doctor_id/service_id values previously returned by
    search_clinics or search_services.
    """
    # Reuses AppointmentSerializer so the assistant is bound by the same
    # double-booking / past-date / clinic-consistency rules as the public API
    # (see AppointmentSerializer.validate in clinics/serializers.py).
    serializer = AppointmentSerializer(data={
        'clinic': clinic_id,
        'doctor': doctor_id,
        'service': service_id,
        'patient_name': patient_name,
        'patient_phone': patient_phone,
        'preferred_date': preferred_date,
        'preferred_time': preferred_time,
        'comment': comment,
    })
    if not serializer.is_valid():
        return {'success': False, 'errors': serializer.errors}

    appointment = serializer.save()
    return {
        'success': True,
        'appointment_id': appointment.id,
        'status': appointment.status,
    }


TOOLS = [search_clinics, search_services, book_appointment]
