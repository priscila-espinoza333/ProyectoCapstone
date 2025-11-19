# core/views_reservas.py (o donde tengas esta vista)
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Reserva
from .emails import enviar_correo_reserva  # 👈 importa el helper

@login_required
def reservas_confirmar(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id, usuario=request.user)

    if request.method == "POST":
        # Aquí pones la lógica que cambia el estado / guarda la reserva
        # por ejemplo:
        # reserva.estado = Reserva.Estado.CONFIRMADA
        # reserva.save()

        enviar_correo_reserva(reserva)   # 👈 AQUÍ SE ENVÍA EL CORREO

        messages.success(request, "Tu reserva ha sido confirmada. Te enviamos el detalle por correo.")
        return redirect("pago_reserva", reserva.id)

    # Si llegas por GET, simplemente muestras algo o rediriges
    return redirect("resumen_reserva", reserva_id=reserva.id)
