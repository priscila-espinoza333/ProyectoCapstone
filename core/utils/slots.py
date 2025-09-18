# core/utils/slots.py
from datetime import datetime, timedelta, time
from django.utils import timezone
from core.models import Reserva, Cancha

def generar_tramos_disponibles(cancha: Cancha, fecha, duracion_min=None):
    """
    Devuelve lista de (inicio, fin) 'aware' para la fecha, respetando:
    - horario del recinto
    - duración de tramo de la cancha
    - solapes con reservas PENDIENTE/CONFIRMADA
    """
    duracion_min = duracion_min or cancha.duracion_tramo_min
    rec = cancha.recinto

    # inicio y fin del día (aware)
    tz = timezone.get_current_timezone()
    start_dt = tz.localize(datetime.combine(fecha, rec.hora_apertura))
    end_dt   = tz.localize(datetime.combine(fecha, rec.hora_cierre))

    # reservas ocupadas del día
    ocupadas = Reserva.objects.filter(
        cancha=cancha,
        estado__in=[Reserva.Estado.PENDIENTE, Reserva.Estado.CONFIRMADA],
        fecha_hora_inicio__lt=end_dt,
        fecha_hora_fin__gt=start_dt,
    ).order_by("fecha_hora_inicio").values_list("fecha_hora_inicio", "fecha_hora_fin")

    # barrer el día por tramos
    cursor = start_dt
    tramos = []
    paso = timedelta(minutes=duracion_min)

    while cursor + paso <= end_dt:
        inicio = cursor
        fin = cursor + paso

        # descartar pasado (si es hoy)
        if inicio < timezone.now():
            cursor += paso
            continue

        # chequear solape contra ocupadas
        solapa = False
        for oi, of in ocupadas:
            if oi < fin and of > inicio:
                solapa = True
                break

        if not solapa:
            tramos.append((inicio, fin))
        cursor += paso

    return tramos
