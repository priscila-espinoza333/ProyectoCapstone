from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError
from django.utils import timezone

from core.models import Reserva, Cancha

def crear_reserva(cancha: Cancha, usuario, inicio, fin, nombre_contacto="", email_contacto="", telefono_contacto=""):
    """
    Crea una reserva atómicamente, revalidando reglas de dominio dentro de la transacción.
    """
    if inicio >= fin:
        raise ValidationError("El horario de fin debe ser posterior al inicio.")

    try:
        with transaction.atomic():
            # Se delega validación fuerte a Reserva.clean() (horario recinto, solapes, pasado)
            reserva = Reserva(
                cancha=cancha,
                usuario=usuario if getattr(usuario, "is_authenticated", False) else None,
                nombre_contacto=nombre_contacto or (getattr(usuario, "get_full_name", lambda: "")() if getattr(usuario, "is_authenticated", False) else ""),
                email_contacto=email_contacto or (getattr(usuario, "email", "") if getattr(usuario, "is_authenticated", False) else ""),
                telefono_contacto=telefono_contacto or "",
                fecha_hora_inicio=inicio,
                fecha_hora_fin=fin,
                estado=Reserva.Estado.PENDIENTE,
            )
            reserva.full_clean()   # dispara todas las validaciones de dominio
            reserva.save()         # calcula precio_total si estaba en 0, por models.py
            return reserva
    except IntegrityError:
        raise ValidationError("Conflicto al crear la reserva. Intenta nuevamente.")
