from datetime import datetime, timedelta, time
from django.utils import timezone
from core.models import Reserva

def generar_tramos_disponibles(cancha, fecha):
    """
    Devuelve lista de pares (inicio_datetime_aware, fin_datetime_aware) libres
    en bloques de cancha.duracion_tramo_min, dentro del horario del recinto.
    Excluye solapados con reservas PENDIENTE/CONFIRMADA.
    """
    tz = timezone.get_current_timezone()
    rec = cancha.recinto

    # Inicio/fin del día en hora local, aware:
    start_dt = timezone.make_aware(datetime.combine(fecha, rec.hora_apertura), tz)
    end_dt   = timezone.make_aware(datetime.combine(fecha, rec.hora_cierre), tz)

    paso = timedelta(minutes=getattr(cancha, "duracion_tramo_min", 60))

    # Carga reservas del día para exclusión
    reservas = Reserva.objects.filter(
        cancha=cancha,
        fecha_hora_inicio__lt=end_dt,
        fecha_hora_fin__gt=start_dt,
        estado__in=[Reserva.Estado.PENDIENTE, Reserva.Estado.CONFIRMADA],
    ).values_list("fecha_hora_inicio", "fecha_hora_fin")

    libres = []
    cursor = start_dt
    while cursor + paso <= end_dt:
        slot_ini = cursor
        slot_fin = cursor + paso

        # Excluir si solapa con una reserva
        ocupado = False
        for r_ini, r_fin in reservas:
            # Asegura aware:
            if timezone.is_naive(r_ini): r_ini = timezone.make_aware(r_ini, tz)
            if timezone.is_naive(r_fin): r_fin = timezone.make_aware(r_fin, tz)
            if not (slot_fin <= r_ini or slot_ini >= r_fin):
                ocupado = True
                break

        if not ocupado:
            libres.append((slot_ini, slot_fin))

        cursor = slot_fin

    return libres