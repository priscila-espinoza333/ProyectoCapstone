from django.db import transaction, IntegrityError, models
from django.core.exceptions import ValidationError
from django.utils import timezone 
from datetime import timedelta
from core.models import Reserva, Cancha, ReservaTemporal, Carrito



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
    
def limpiar_reservas_expiradas():
    #Elimina las reservas temporales que no han sido pagadas el cual en expira_en < ahora.

    expiradas = ReservaTemporal.objects.filter(pagada=False, expira_en__lt=timezone.now())
    count = expiradas.count()
    expiradas.delete()
    return count

def crear_reserva_en_carrito(carrito, cancha, hora_inicio=None):
    #Se crea una reserva de 1 hora en el carrito, Si hora_inicio es None, usa timezone.now()
    
    from datetime import  timedelta 
    from django.utils import timezone as djtz
    if hora_inicio is None:
        hora_inicio = djtz.now()
    hora_fin = hora_inicio + timedelta(hours=1)
    Reserva = ReservaTemporal.objects.create(
        carrito= carrito,
        cancha = cancha,
        hora_inicio = hora_inicio,
        hora_fin = hora_fin,
        precio = cancha.precio_hora
    )
    return Reserva