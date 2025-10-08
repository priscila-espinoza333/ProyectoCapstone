# core/views.py
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from core.forms import ReservaForm, SignUpForm
from core.models import Cancha, Reserva, ReservaTemporal
from core.services.reservas import crear_reserva
from core.utils.slots import generar_tramos_disponibles
from django.core.mail import EmailMultiAlternatives
from transbank.webpay.webpay_plus.transaction import Transaction
from datetime import datetime, timedelta
from .models import ReservaTemporal
# -----------------------------
# PÁGINAS EXISTENTES
# -----------------------------

def index(request):
    # Tu index extiende "core/base.html", por eso el path empieza con "core/"
    return render(request, "core/index.html")


def canchas(request, deporte: str | None = None):
    """
    Listado general de canchas, con filtro opcional por deporte.
    Renderiza: core/canchas/lista.html
    """
    qs = Cancha.objects.select_related("recinto").filter(activa=True)
    deportes = {c[0]: c[1] for c in Cancha.Deporte.choices}  # {"FUTBOL": "Fútbol", ...}

    deporte_slug = None
    if deporte:
        deporte_slug = deporte.upper()
        qs = qs.filter(deporte=deporte_slug)

    return render(
        request,
        "core/canchas/lista.html",
        {
            "canchas": qs.order_by("recinto__nombre", "nombre"),
            "deportes": deportes,
            "deporte_actual": deporte_slug,
        },
    )


# -----------------------------
# FLUJO DE RESERVAS
# -----------------------------

def cancha_detalle(request, pk: int):
    """
    Detalle de cancha + formulario de reserva y tramos disponibles.
    Renderiza: core/canchas/detalle.html
    """
    cancha = get_object_or_404(Cancha.objects.select_related("recinto"), pk=pk, activa=True)
    form = ReservaForm(initial={"cancha_id": cancha.id})

    reservas_del_dia = []
    tramos_disponibles = []
    fecha_qs = request.GET.get("fecha")

    if fecha_qs:
        try:
            fecha = datetime.fromisoformat(fecha_qs).date()
            reservas_del_dia = (
                Reserva.objects.filter(
                    cancha=cancha,
                    fecha_hora_inicio__date=fecha,
                    estado__in=[Reserva.Estado.PENDIENTE, Reserva.Estado.CONFIRMADA],
                )
                .order_by("fecha_hora_inicio")
            )
            tramos_disponibles = generar_tramos_disponibles(cancha, fecha)
        except ValueError:
            pass

    return render(
        request,
        "core/canchas/detalle.html",
        {
            "cancha": cancha,
            "form": form,
            "reservas_del_dia": reservas_del_dia,
            "tramos_disponibles": tramos_disponibles,
        },
    )


def reserva_crear(request, cancha_id: int):
    """
    Procesa el formulario y crea una reserva en estado PENDIENTE.
    - POST válido: redirige a resumen.
    - GET: vuelve a mostrar el detalle con el form inicial.
    Renderiza (en GET o error): core/canchas/detalle.html
    """
    cancha = get_object_or_404(Cancha, pk=cancha_id, activa=True)

    if request.method == "POST":
        form = ReservaForm(request.POST)
        if form.is_valid():
            try:
                reserva = crear_reserva(
                    cancha=form.cleaned_data["cancha"],
                    usuario=request.user,
                    inicio=form.cleaned_data["inicio"],
                    fin=form.cleaned_data["fin"],
                    nombre_contacto=form.cleaned_data.get("nombre_contacto", ""),
                    email_contacto=form.cleaned_data.get("email_contacto", ""),
                    telefono_contacto=form.cleaned_data.get("telefono_contacto", ""),
                )
                messages.success(request, "Reserva creada. Revisa el resumen.")
                return redirect("reservas_resumen", reserva_id=reserva.id)
            except Exception as e:
                messages.error(request, str(e))
        else:
            messages.error(request, "Por favor corrige los errores del formulario.")
    else:
        form = ReservaForm(initial={"cancha_id": cancha.id})

    # En caso de GET o errores, re-render del detalle con el form y la cancha.
    return render(
        request,
        "core/canchas/detalle.html",
        {"cancha": cancha, "form": form, "reservas_del_dia": [], "tramos_disponibles": []},
    )


def reservas_resumen(request, reserva_id: int):
    """
    Muestra el resumen de la reserva antes de confirmar.
    Renderiza: core/reservas/resumen.html
    """
    reserva = get_object_or_404(Reserva.objects.select_related("cancha__recinto"), pk=reserva_id)
    return render(request, "core/reservas/resumen.html", {"reserva": reserva})

# -----------------------------
# FLUJO DE PAGO DE RESERVA
# -----------------------------

@login_required
def pago_reserva(request, reserva_id):
    reserva = get_object_or_404(ReservaTemporal, id=reserva_id, usuario=request.user)
    if reserva.esta_expirada():
        reserva.delete()
        return render(request, "core/reservas/pago_fallido.html", {"error": "La reserva expiró (5 minutos sin pago)"},
        )
    return render(request, "core/reservas/carrito.html", {"reserva": reserva})

@login_required
def iniciar_pago_reserva(request, reserva_id):
    reserva = get_object_or_404(ReservaTemporal, id=reserva_id, usuario=request.user)
    tx = Transaction()
    response = tx.create(
        buy_order=str(reserva.id),
        session_id=str(request.user.id),
        amount=float(reserva.precio),
        return_url=request.build_absolute_uri("/confirmar_pago_reserva/"),
    )
    return redirect(response['url'] + "?token_ws=" + response['token'])

@login_required
def confirmar_pago_reserva(request):
    token = request.GET.get("token_ws")
    tx = Transaction()
    response = tx.commit(token)
    reserva = get_object_or_404(ReservaTemporal, id=response['buy_order'])
    
    if response.get("status") in ('AUTHORIZED',):
        reserva.pagada = True
        reserva.save()
        return render(request, "core/reservas/exito.html", {"reserva": reserva})
    else:
        reserva.delete()
    #return render(request,"core/reservas/pago_fallido.html",{"error": "El pago fue rechazado o cancelado."})
    send_mail(
            subject="Reserva Confirmada - MatchPlay",
            message=(
                f"Tu reserva ha sido confirmada correctamente!!.\n\n"
                f"Cancha: {reserva.cancha.nombre}\n"
                f"Horario: {reserva.hora_inicio.strftime('%d/%m/%Y %H:%M')} - "
                f"{reserva.hora_fin.strftime('%H:%M')}\n"
                f"Total Pagado: ${reserva.precio}\n\n"
                f"Gracias por Reservar con MatchPlay."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[request.user.email, "contacto@matchplay.cl"],
            fail_silently=False,
    )
    return render(request,"core/reservas/pago_fallido.html",{"error": "El pago fue rechazado o cancelado."})
    print("Transbank create response:", response)
#-----------------------------------------------------

@login_required
@require_http_methods(["GET", "POST"])
@transaction.atomic
def reservas_confirmar(request, reserva_id: int):
    """
    Confirma una reserva del usuario autenticado.
    Reglas:
    - Debe pertenecer al usuario.
    - No debe estar cancelada.
    - No debe estar expirada (ya iniciada o pasada).
    - Si ya estaba confirmada, simplemente muestra la pantalla de éxito.

    Renderiza:
    - core/reservas/error_estado.html en caso de no poder confirmar.
    - core/reservas/confirmacion.html en caso de éxito.
    """

    r = get_object_or_404(
        Reserva.objects.select_related("cancha", "cancha__recinto"),
        pk=reserva_id,
        usuario=request.user,
    )

    # 1) No se puede confirmar una reserva cancelada
    if r.estado == Reserva.Estado.CANCELADA:
        return render(
            request,
            "core/reservas/error_estado.html",
            {"titulo": "NO SE PUEDE CONFIRMAR", "mensaje": "Esta reserva fue cancelada."},
            status=409,
        )

    # 2) No se puede confirmar si ya inició / expiró
    if timezone.now() >= r.fecha_hora_inicio:
        return render(
            request,
            "core/reservas/error_estado.html",
            {
                "titulo": "RESERVA EXPIRADA",
                "mensaje": "No puedes confirmar una reserva que ya inició o finalizó.",
            },
            status=409,
        )

    # 3) Si ya estaba confirmada, muestra éxito igual (idempotencia "friendly")
    if r.estado == Reserva.Estado.CONFIRMADA:
        return render(request, "core/reservas/confirmacion.html", {"reserva": r})

    # 4) Transición de estado → CONFIRMADA
    r.estado = Reserva.Estado.CONFIRMADA
    r.save(update_fields=["estado", "precio_total", "actualizado_en"])

    # 5) Enviar correo de confirmación (Punto C)
    try:
        from django.template.loader import render_to_string
        from django.utils.html import strip_tags

        subject = f"Confirmación de Reserva #{r.id}"
        html_message = render_to_string("core/emails/reserva_confirmada.html", {"reserva": r})
        plain_message = strip_tags(html_message)
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [r.email_contacto or request.user.email]

        send_mail(subject, plain_message, from_email, recipient_list, html_message=html_message)
    except Exception as e:
        messages.warning(request, f"No se pudo enviar el correo de confirmación: {e}")

    # 6) Mostrar la página de confirmación
    return render(request, "core/reservas/confirmacion.html", {"reserva": r})

   

def reservas_exito(request, reserva_id: int):
    """
    Pantalla final de éxito (alias a confirmación).
    Renderiza: core/reservas/confirmacion.html
    """
    reserva = get_object_or_404(Reserva, pk=reserva_id)
    return render(request, "core/reservas/confirmacion.html", {"reserva": reserva})


@login_required
def mis_reservas(request):
    """
    Listado de reservas del usuario.
    Renderiza: core/reservas/mis_reservas.html
    """
    qs = (
        Reserva.objects.select_related("cancha__recinto")
        .filter(usuario=request.user)
        .order_by("-fecha_hora_inicio")
    )
    paginator = Paginator(qs, 10)
    page = request.GET.get("page")
    reservas = paginator.get_page(page)
    return render(request, "core/reservas/mis_reservas.html", {"reservas": reservas})


@login_required
@require_http_methods(["POST", "GET"])
def reservas_cancelar(request, reserva_id: int):
    """
    Cancela una reserva del usuario respetando reglas de negocio.
    Renderiza:
    - core/reservas/error_estado.html (expirada / no permitida / ya cancelada)
    - core/reservas/cancelada.html (éxito)
    - core/reservas/cancelar_confirm.html (GET confirmación)
    """
    r = get_object_or_404(Reserva, pk=reserva_id, usuario=request.user)

    # 1) Expirada (ya inició o pasó)
    if timezone.now() >= r.fecha_hora_inicio:
        return render(
            request,
            "core/reservas/error_estado.html",
            {
                "titulo": "RESERVA EXPIRADA",
                "mensaje": "Esta reserva ya inició o finalizó. No es posible cancelarla.",
            },
            status=409,  # Conflict
        )

    # 2) Ventana de cancelación (< 2 horas)
    if r.fecha_hora_inicio - timezone.now() < timedelta(hours=2):
        return render(
            request,
            "core/reservas/error_estado.html",
            {
                "titulo": "CANCELACIÓN NO PERMITIDA",
                "mensaje": "No es posible cancelar con menos de 2 horas de anticipación.",
            },
            status=403,  # Forbidden
        )

    # 3) Ya cancelada / estado no cancelable
    if r.estado == Reserva.Estado.CANCELADA:
        return render(
            request,
            "core/reservas/error_estado.html",
            {"titulo": "YA CANCELADA", "mensaje": "La reserva ya se encontraba cancelada."},
            status=200,
        )

    # 4) POST -> cancelar
    if request.method == "POST":
        r.estado = Reserva.Estado.CANCELADA
        r.save(update_fields=["estado"])
        # Muestra la página de éxito
        return render(request, "core/reservas/cancelada.html", {"reserva": r})

    # 5) GET -> confirmar
    return render(request, "core/reservas/cancelar_confirm.html", {"reserva": r})


def canchas_categorias(request):
    """
    Landing opcional de categorías de canchas.
    Renderiza: core/canchas/categorias.html
    """
    return render(request, "core/canchas/categorias.html")


# -----------------------------
# AUTENTICACIÓN (REGISTRO)
# -----------------------------

@require_http_methods(["GET", "POST"])
def signup(request):
    if request.user.is_authenticated:
        return redirect("index")

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, "¡Cuenta creada! Bienvenid@ 👋")
            return redirect("mis_reservas")
        else:
            messages.error(request, "Por favor corrige los errores del formulario.")
    else:
        form = SignUpForm()

    return render(request, "core/auth/signup.html", {"form": form})
