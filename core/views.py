from __future__ import annotations

from datetime import datetime, timedelta
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordResetForm
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from core.forms import ReservaForm
from core.models import Cancha, Reserva, ReservaTemporal
from core.services.reservas import crear_reserva
from core.utils.slots import generar_tramos_disponibles
from users.forms import SignUpForm, ProfileForm
from django.core.mail import EmailMultiAlternatives
from transbank.webpay.webpay_plus.transaction import Transaction
from datetime import datetime, timedelta
from .models import ReservaTemporal
# -----------------------------
# PÁGINAS EXISTENTES
# -----------------------------


# ------------------------------------------------------------
# Utilidades
# ------------------------------------------------------------
def _as_aware_datetime(x):
    """
    Convierte str/datetime a datetime aware en la TZ del proyecto.
    Acepta ISO con 'Z' o desplazamientos (+00:00).
    """
    if isinstance(x, datetime):
        dt = x
    elif isinstance(x, str):
        s = x.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
    else:
        return x

    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def solo_admin_recinto(view_func):
    """
    Permite solo usuarios autenticados con rol == 'ADMIN_RECINTO'.
    No autenticado -> login; autenticado sin rol -> 403.
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        u = request.user
        if not u.is_authenticated:
            return redirect("login")
        if getattr(u, "rol", "") != "ADMIN_RECINTO":
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped


# ------------------------------------------------------------
# Páginas públicas
# ------------------------------------------------------------
def index(request):
    return render(request, "core/index.html")


def canchas(request, deporte: str | None = None):
    """
    Listado de canchas con filtros por deporte, búsqueda, orden y paginación.
    """
    qs = Cancha.objects.select_related("recinto").filter(activa=True)
    deportes = {c[0]: c[1] for c in Cancha.Deporte.choices}

    # Filtro por deporte (slug o ?deporte=)
    deporte_actual = None
    dep_qs = request.GET.get("deporte")
    if deporte:
        deporte_actual = deporte.upper()
    elif dep_qs:
        deporte_actual = dep_qs.upper()
    if deporte_actual:
        qs = qs.filter(deporte=deporte_actual)

    # Búsqueda
    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(
            Q(nombre__icontains=q)
            | Q(recinto__nombre__icontains=q)
            | Q(descripcion__icontains=q)
        )

    # Orden
    orden = request.GET.get("orden")
    if orden == "nombre":
        qs = qs.order_by("nombre")
    elif orden == "-nombre":
        qs = qs.order_by("-nombre")
    elif orden == "precio":
        qs = qs.order_by("precio_hora", "nombre")
    elif orden == "-precio":
        qs = qs.order_by("-precio_hora", "nombre")
    else:
        qs = qs.order_by("recinto__nombre", "nombre")

    # Paginación
    paginator = Paginator(qs, 12)
    page = request.GET.get("page")
    canchas_page = paginator.get_page(page)

    return render(
        request,
        "core/canchas/lista.html",
        {
            "canchas": canchas_page,
            "deportes": deportes,
            "deporte_actual": deporte_actual,
            "q": q,
            "orden": orden,
        },
    )


# ------------------------------------------------------------
# Detalle de Cancha + reserva
# ------------------------------------------------------------
def cancha_detalle(request, pk: int):
    cancha = get_object_or_404(
        Cancha.objects.select_related("recinto"), pk=pk, activa=True
    )

    fecha_actual = None
    reservas_del_dia = []
    tramos = []

    fecha_qs = request.GET.get("fecha")
    if fecha_qs:
        try:
            # yyyy-mm-dd -> date
            fecha_actual = datetime.fromisoformat(fecha_qs).date()

            # reservas del día (para mostrar a la izquierda)
            reservas_del_dia = (
                Reserva.objects.filter(
                    cancha=cancha,
                    fecha_hora_inicio__date=fecha_actual,
                    estado__in=[Reserva.Estado.PENDIENTE, Reserva.Estado.CONFIRMADA],
                ).order_by("fecha_hora_inicio")
            )

            # pares (inicio, fin) disponibles — deben ser AWARE
            pares = generar_tramos_disponibles(cancha, fecha_actual)

            # Precio por tramo y datos para el template
            for ini, fin in pares:
                # asegurar aware
                if timezone.is_naive(ini):
                    ini = timezone.make_aware(ini, timezone.get_current_timezone())
                if timezone.is_naive(fin):
                    fin = timezone.make_aware(fin, timezone.get_current_timezone())

                tramos.append({
                    "inicio": ini,
                    "fin": fin,
                    "precio": cancha.calcular_precio(ini, fin),  # Decimal OK en template
                })
        except ValueError:
            # fecha inválida -> sin tramos
            fecha_actual = None

    return render(
        request,
        "core/canchas/detalle.html",
        {
            "cancha": cancha,
            "fecha_actual": fecha_actual,
            "reservas_del_dia": reservas_del_dia,
            "tramos": tramos,
        },
    )


@require_http_methods(["GET", "POST"])
def reserva_crear(request, cancha_id: int):
    """
    Procesa la creación de una reserva (POST) esperando los campos:
      - cancha (id), inicio (ISO), fin (ISO), nombre/email/teléfono (opcionales)
    Si GET o error de validación, vuelve al detalle.
    """
    cancha = get_object_or_404(Cancha, pk=cancha_id, activa=True)

    if request.method == "POST":
        form = ReservaForm(request.POST)
        if form.is_valid():
            try:
                reserva = crear_reserva(
                    cancha=form.cleaned_data["cancha"],
                    usuario=request.user if request.user.is_authenticated else None,
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

    # GET o error -> volvemos al detalle sin fecha
    return render(
        request,
        "core/canchas/detalle.html",
        {
            "cancha": cancha,
            "reservas_del_dia": [],
            "tramos": [],
        },
    )


def reservas_resumen(request, reserva_id: int):
    reserva = get_object_or_404(
        Reserva.objects.select_related("cancha__recinto"), pk=reserva_id
    )
    return render(request, "core/reservas/resumen.html", {"reserva": reserva})


# ------------------------------------------------------------
# Pago de reservas (individual)
# ------------------------------------------------------------
@login_required
def pago_reserva(request, reserva_id):
    reserva = get_object_or_404(ReservaTemporal, id=reserva_id, usuario=request.user)
    if reserva.esta_expirada():
        reserva.delete()
        return render(
            request,
            "core/reservas/pago_fallido.html",
            {"error": "La reserva expiró (5 minutos sin pago)."},
        )

    return render(request, "core/reservas/pago_reserva.html", {"reserva": reserva})


@login_required
def iniciar_pago_reserva(request, reserva_id):
    from transbank.webpay.webpay_plus.transaction import Transaction

    reserva = get_object_or_404(ReservaTemporal, id=reserva_id, usuario=request.user)
    tx = Transaction()
    response = tx.create(
        buy_order=str(reserva.id),
        session_id=str(request.user.id),
        amount=float(reserva.precio),
        return_url=request.build_absolute_uri(reverse("confirmar_pago_reserva")),
    )
    return redirect(response["url"] + "?token_ws=" + response["token"])


@login_required
def confirmar_pago_reserva(request):
    from transbank.webpay.webpay_plus.transaction import Transaction

    token = request.GET.get("token_ws")
    tx = Transaction()
    response = tx.commit(token)
    reserva = get_object_or_404(ReservaTemporal, id=response["buy_order"])

    if response.get("status") == "AUTHORIZED":
        reserva.pagada = True
        reserva.save()
        return render(request, "core/reservas/exito.html", {"reserva": reserva})
    else:
        reserva.delete()
        return render(
            request,
            "core/reservas/pago_fallido.html",
            {"error": "El pago no fue autorizado."},
        )


# ------------------------------------------------------------
# Confirmar / Cancelar / Mis reservas
# ------------------------------------------------------------
@login_required
@require_http_methods(["GET", "POST"])
@transaction.atomic
def reservas_confirmar(request, reserva_id: int):
    r = get_object_or_404(
        Reserva.objects.select_related("cancha", "cancha__recinto"),
        pk=reserva_id,
        usuario=request.user,
    )

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

    if r.estado == Reserva.Estado.CONFIRMADA:
        return render(request, "core/reservas/confirmacion.html", {"reserva": r})

    r.estado = Reserva.Estado.CONFIRMADA
    r.save(update_fields=["estado", "actualizado_en"])
    messages.success(request, "¡Reserva confirmada!")
    return render(request, "core/reservas/confirmacion.html", {"reserva": r})


@login_required
@require_http_methods(["POST", "GET"])
def reservas_cancelar(request, reserva_id: int):
    r = get_object_or_404(Reserva, pk=reserva_id, usuario=request.user)

    # 1) Expirada
    if timezone.now() >= r.fecha_hora_inicio:
        return render(
            request,
            "core/reservas/error_estado.html",
            {
                "titulo": "RESERVA EXPIRADA",
                "mensaje": "Esta reserva ya inició o finalizó. No es posible cancelarla.",
            },
            status=409,
        )

    # 2) Menos de 2 horas
    if r.fecha_hora_inicio - timezone.now() < timedelta(hours=2):
        return render(
            request,
            "core/reservas/error_estado.html",
            {
                "titulo": "CANCELACIÓN NO PERMITIDA",
                "mensaje": "No es posible cancelar con menos de 2 horas de anticipación.",
            },
            status=403,
        )

    # 3) Ya cancelada
    if r.estado == Reserva.Estado.CANCELADA:
        return render(
            request,
            "core/reservas/error_estado.html",
            {
                "titulo": "YA CANCELADA",
                "mensaje": "La reserva ya se encontraba cancelada.",
            },
            status=200,
        )

    # 4) POST -> cancelar
    if request.method == "POST":
        r.estado = Reserva.Estado.CANCELADA
        r.save(update_fields=["estado"])
        return render(request, "core/reservas/cancelada.html", {"reserva": r})

    # 5) GET -> confirmar
    return render(request, "core/reservas/cancelar_confirm.html", {"reserva": r})


def reservas_exito(request, reserva_id: int):
    reserva = get_object_or_404(
        Reserva.objects.select_related("cancha__recinto"),
        pk=reserva_id,
    )
    return render(request, "core/reservas/confirmacion.html", {"reserva": reserva})


@login_required
def mis_reservas(request):
    qs = (
        Reserva.objects.select_related("cancha__recinto")
        .filter(usuario=request.user)
        .order_by("-fecha_hora_inicio")
    )
    paginator = Paginator(qs, 10)
    page_number = request.GET.get("page")
    reservas = paginator.get_page(page_number)
    return render(request, "core/reservas/mis_reservas.html", {"reservas": reservas})


# ------------------------------------------------------------
# Admin / Perfil / Registro
# ------------------------------------------------------------
@solo_admin_recinto
def panel_admin(request):
    return render(request, "core/panel_admin.html")


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
        messages.error(request, "Por favor corrige los errores del formulario.")
    else:
        form = SignUpForm()

    return render(request, "core/auth/signup.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def perfil(request):
    """
    Form de perfil. No permite cambiar email.
    """
    if request.method == "POST" and request.POST.get("action") == "update_profile":
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = request.user.email  # blindaje
            user.save(update_fields=["first_name", "last_name", "username"])
            messages.success(request, "Perfil actualizado correctamente.")
            return redirect("perfil")
        messages.error(request, "Por favor corrige los errores del formulario.")
    else:
        form = ProfileForm(instance=request.user)

    return render(
        request, "core/auth/profile.html", {"form": form, "user_obj": request.user}
    )


@login_required
@require_POST
def enviar_link_reset(request):
    """
    Envía un correo con el enlace de reseteo de contraseña al email del usuario.
    """
    user = request.user
    if not user.email:
        messages.error(request, "Tu cuenta no tiene correo configurado.")
        return redirect("perfil")

    form = PasswordResetForm({"email": user.email})
    if form.is_valid():
        form.save(
            request=request,
            use_https=request.is_secure(),
            email_template_name="core/auth/emails/password_reset_email.txt",
            html_email_template_name="core/auth/emails/password_reset_email.html",
            subject_template_name="core/auth/emails/password_reset_subject.txt",
        )
        messages.success(request, "📩 Te enviamos un enlace para cambiar tu contraseña.")
        return redirect("perfil")

    messages.error(request, "No se pudo enviar el correo. Revisa tu email.")
    return redirect("perfil")
