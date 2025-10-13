# core/views_cart.py
from datetime import datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST

from transbank.webpay.webpay_plus.transaction import Transaction
from core.models import Carrito, ReservaTemporal, Cancha


# -----------------------------
# Helpers
# -----------------------------
def _parse_iso_to_aware(value: str | None):
    """
    Convierte '2025-10-31T18:00:00Z' o con offset a datetime aware en la TZ actual.
    """
    if not value:
        return None
    dt = parse_datetime(value.replace("Z", "+00:00"))
    if not dt:
        return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _get_or_create_carrito(user):
    carrito, _ = Carrito.objects.get_or_create(usuario=user, pagado=False)
    return carrito


# compat con código previo que llamaba a obtener_carrito(request)
def obtener_carrito(request):
    return _get_or_create_carrito(request.user)


def _back_to_cancha(request, cancha_id: int):
    """
    Vuelve a la página anterior si existe; si no, al detalle de la cancha.
    """
    ref = request.META.get("HTTP_REFERER")
    if ref:
        return redirect(ref)
    return redirect(reverse("cancha_detalle", kwargs={"pk": cancha_id}))


def _carrito_total_float(carrito: Carrito) -> float:
    """
    Adapta si tu Carrito expone total como property (carrito.total)
    o como método (carrito.total()).
    """
    total = getattr(carrito, "total", None)
    if callable(total):
        return float(total())
    return float(total or 0)


# -----------------------------
# Carrito
# -----------------------------
@login_required
@require_POST
def agregar_reserva(request, cancha_id):
    """
    Agrega al carrito una ReservaTemporal con inicio/fin recibidos por POST.
    El template ya une 1 o 2 tramos consecutivos en un solo rango (inicio–fin).
    """
    cancha = get_object_or_404(Cancha, id=cancha_id, activa=True)

    inicio = _parse_iso_to_aware(request.POST.get("inicio"))
    fin    = _parse_iso_to_aware(request.POST.get("fin"))

    # Validaciones básicas
    if not inicio or not fin:
        messages.error(request, "Debes seleccionar un horario válido.")
        return _back_to_cancha(request, cancha_id)

    if fin <= inicio:
        messages.error(request, "La hora de término debe ser posterior a la de inicio.")
        return _back_to_cancha(request, cancha_id)

    # (Opcional) validar horario del recinto si tienes helper
    try:
        rec = cancha.recinto
        if hasattr(rec, "horario_valido"):
            mismo_dia = (inicio.date() == fin.date())
            if not (mismo_dia and rec.horario_valido(inicio, fin)):
                messages.error(request, "El rango seleccionado está fuera del horario del recinto.")
                return _back_to_cancha(request, cancha_id)
    except Exception:
        pass

    # Validar disponibilidad si tu modelo lo expone
    try:
        if hasattr(cancha, "tiene_disponibilidad") and not cancha.tiene_disponibilidad(inicio, fin):
            messages.error(request, "La cancha no está disponible en ese horario.")
            return _back_to_cancha(request, cancha_id)
    except Exception:
        pass

    carrito = _get_or_create_carrito(request.user)

    # Precio
    precio = cancha.calcular_precio(inicio, fin)

    # Detecta nombres de campos de fecha/hora en ReservaTemporal
    campos = {f.name for f in ReservaTemporal._meta.get_fields()}
    data = {
        "carrito": carrito,
        "cancha": cancha,
        "precio": precio,
        "pagada": False,
    }
    if "inicio" in campos and "fin" in campos:
        data["inicio"] = inicio
        data["fin"] = fin
    elif "hora_inicio" in campos and "hora_fin" in campos:
        data["hora_inicio"] = inicio
        data["hora_fin"] = fin
    else:
        messages.error(request, "No se pudo crear la reserva temporal (campos de hora no encontrados).")
        return _back_to_cancha(request, cancha_id)

    # Crear hold temporal
    ReservaTemporal.objects.create(**data)

    messages.success(request, "Se agregó tu selección al carrito ✅")
    return redirect("ver_carrito")


@login_required
def ver_carrito(request):
    carrito = _get_or_create_carrito(request.user)

    # Limpia reservas temporales expiradas (usa tu related_name='reservas')
    eliminadas = 0
    for r in list(carrito.reservas.all()):
        if hasattr(r, "esta_expirada") and r.esta_expirada():
            r.delete()
            eliminadas += 1
    if eliminadas:
        messages.info(request, f"Se eliminaron {eliminadas} reservas expiradas del carrito.")

    carrito.refresh_from_db()
    return render(request, "core/reservas/carrito.html", {"carrito": carrito})


@login_required
def iniciar_pago_carrito(request, carrito_id):
    carrito = get_object_or_404(Carrito, id=carrito_id, usuario=request.user, pagado=False)

    # validar expiraciones antes de cobrar
    for r in list(carrito.reservas.all()):
        if hasattr(r, "esta_expirada") and r.esta_expirada():
            carrito.reservas.all().delete()
            messages.error(request, "Alguna reserva expiró. Vuelve a seleccionar horarios.")
            return redirect("ver_carrito")

    tx = Transaction()
    amount = _carrito_total_float(carrito)

    response = tx.create(
        buy_order=str(carrito.id),
        session_id=str(request.user.id),
        amount=amount,
        return_url=request.build_absolute_uri(reverse("confirmar_pago_carrito")),
    )

    return redirect(response["url"] + "?token_ws=" + response["token"])


@login_required
def confirmar_pago_carrito(request):
    token = request.GET.get("token_ws")
    if not token:
        messages.error(request, "Token de pago inválido.")
        return redirect("ver_carrito")

    tx = Transaction()
    response = tx.commit(token)

    carrito = get_object_or_404(Carrito, id=response.get("buy_order"))

    if response.get("status") in ("AUTHORIZED", "AUTHORIZED_TO_CAPTURE", "APPROVED"):
        carrito.pagado = True
        carrito.save()
        for reserva in carrito.reservas.all():
            reserva.pagada = True
            reserva.save()
        return render(request, "core/reservas/pago_exitoso.html", {"carrito": carrito})

    # Si falla: liberar reservas y borrar carrito
    carrito.reservas.all().delete()
    carrito.delete()
    return render(request, "core/reservas/pago_fallido.html", {"error": "El pago no fue autorizado."})

@login_required
@require_POST
def eliminar_reserva_carrito(request, reserva_id):
    """Elimina una reserva temporal específica del carrito del usuario."""
    reserva = get_object_or_404(
        ReservaTemporal,
        id=reserva_id,
        carrito__usuario=request.user,
        carrito__pagado=False
    )
    reserva.delete()
    messages.success(request, "Reserva eliminada del carrito 🗑️")
    return redirect("ver_carrito")
