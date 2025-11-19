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
from django.db.models import Q, Count, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth import get_user_model
from calendar import monthrange
from datetime import date 



from core.forms import ReservaForm
from core.models import Cancha, Reserva, ReservaTemporal
from core.services.reservas import crear_reserva
from core.utils.slots import generar_tramos_disponibles
from users.forms import SignUpForm, ProfileForm
from django.core.mail import EmailMultiAlternatives
from transbank.webpay.webpay_plus.transaction import Transaction
from datetime import datetime, timedelta
from .models import Carrito, ReservaTemporal
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
    hoy = timezone.localdate()
    ahora = timezone.now()

    # --- KPIs de reservas ---
    # 1) Reservas que se JUEGAN hoy (pendientes o confirmadas)
    reservas_hoy = Reserva.objects.filter(
        fecha_hora_inicio__date=hoy,
        estado__in=[Reserva.Estado.PENDIENTE, Reserva.Estado.CONFIRMADA],
    ).count()

    # 2) Reservas CREADAS hoy
    reservas_creadas_hoy = Reserva.objects.filter(
        creado_en__date=hoy
    ).count()

    # 3) Reservas próximas (siguientes 7 días)
    en_7_dias = hoy + timedelta(days=7)
    reservas_proximas_7 = Reserva.objects.filter(
        fecha_hora_inicio__date__gte=hoy,
        fecha_hora_inicio__date__lte=en_7_dias,
        estado__in=[Reserva.Estado.PENDIENTE, Reserva.Estado.CONFIRMADA],
    ).count()

    total_canchas = Cancha.objects.filter(activa=True).count()

    UserModel = get_user_model()
    usuarios_activos = UserModel.objects.filter(is_active=True).count()

    # --- Ingresos por periodos ---
    base_ingresos = Reserva.objects.filter(
        estado=Reserva.Estado.CONFIRMADA
    )

    # 🔹 Ingresos últimos 7 días (ventana móvil)
    hace_7_dias = hoy - timedelta(days=7)
    ingresos_7d = (
        base_ingresos.filter(
            fecha_hora_inicio__date__gte=hace_7_dias,
            fecha_hora_inicio__date__lte=hoy,
        ).aggregate(total=Sum("precio_total"))["total"]
        or 0
    )

    # 🔹 Mes actual (1 al último día del mes)
    year = hoy.year
    month = hoy.month
    start_mes_actual = date(year, month, 1)
    last_day_mes_actual = monthrange(year, month)[1]
    end_mes_actual = date(year, month, last_day_mes_actual)

    ingresos_mes_actual = (
        base_ingresos.filter(
            fecha_hora_inicio__date__gte=start_mes_actual,
            fecha_hora_inicio__date__lte=end_mes_actual,
        ).aggregate(total=Sum("precio_total"))["total"]
        or 0
    )

    # 🔹 Mes anterior (1 al último día del mes anterior)
    if month == 1:
        prev_year = year - 1
        prev_month = 12
    else:
        prev_year = year
        prev_month = month - 1

    start_mes_anterior = date(prev_year, prev_month, 1)
    last_day_mes_anterior = monthrange(prev_year, prev_month)[1]
    end_mes_anterior = date(prev_year, prev_month, last_day_mes_anterior)

    ingresos_mes_anterior = (
        base_ingresos.filter(
            fecha_hora_inicio__date__gte=start_mes_anterior,
            fecha_hora_inicio__date__lte=end_mes_anterior,
        ).aggregate(total=Sum("precio_total"))["total"]
        or 0
    )

    # 🔹 Semestre actual (6 meses)
    # 1° semestre: 1 Ene – 30 Jun
    # 2° semestre: 1 Jul – 31 Dic
    if month <= 6:
        start_semestre = date(year, 1, 1)
        end_semestre = date(year, 6, 30)
    else:
        start_semestre = date(year, 7, 1)
        end_semestre = date(year, 12, 31)

    ingresos_semestre = (
        base_ingresos.filter(
            fecha_hora_inicio__date__gte=start_semestre,
            fecha_hora_inicio__date__lte=end_semestre,
        ).aggregate(total=Sum("precio_total"))["total"]
        or 0
    )

    contexto = {
        # KPIs reservas
        "reservas_hoy": reservas_hoy,
        "reservas_creadas_hoy": reservas_creadas_hoy,
        "reservas_proximas_7": reservas_proximas_7,
        "total_canchas": total_canchas,
        "usuarios_activos": usuarios_activos,

        # Ingresos
        "ingresos_7d": ingresos_7d,
        "ingresos_mes_actual": ingresos_mes_actual,
        "ingresos_mes_anterior": ingresos_mes_anterior,
        "ingresos_semestre": ingresos_semestre,

        # Fechas de referencia para mostrar en el template
        "hoy": hoy,
        "start_mes_actual": start_mes_actual,
        "end_mes_actual": end_mes_actual,
        "start_mes_anterior": start_mes_anterior,
        "end_mes_anterior": end_mes_anterior,
        "start_semestre": start_semestre,
        "end_semestre": end_semestre,
    }
    return render(request, "core/panel_admin.html", contexto)




@require_http_methods(["GET", "POST"])
def signup(request):
    if request.user.is_authenticated:
        return redirect("index")

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():

            # Crear usuario inactivo
            user = form.save(commit=False)
            user.is_active = False
            user.save()

            # Enviar correo de verificación
            _enviar_correo_verificacion(request, user)

            messages.success(
                request,
                "Tu cuenta ha sido creada. Te enviamos un correo para activarla 🔐."
            )
            return redirect("login")

        messages.error(request, "Por favor corrige los errores del formulario.")
    else:
        form = SignUpForm()

    return render(request, "core/auth/signup.html", {"form": form})

@login_required
def post_login_redirect(request):
    user = request.user

    # Si es administrador de recinto → panel admin
    if getattr(user, "rol", "") == "ADMIN_RECINTO":
        return redirect("panel_admin")

    # Usuarios normales → mis reservas    
    return redirect("mis_reservas")

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
        messages.success(request, "Te enviamos un enlace para cambiar tu contraseña.")
        return redirect("perfil")

    messages.error(request, "No se pudo enviar el correo. Revisa tu email.")
    return redirect("perfil")

@staff_member_required
def bi_dashboard(request):
    return render(request, "admin/bi_dashboard.html")

@login_required
def pagos_seleccionar(request, carrito_id):
    carrito = get_object_or_404(Carrito, id=carrito_id, usuario=request.user)
    return render(request, "core/pagos/seleccionar.html", {"carrito": carrito})


## Funcion auxiliar para envio de correo de confirmacion

def _enviar_correo_verificacion(request, user):
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    activation_link = request.build_absolute_uri(
        reverse("activar_cuenta", kwargs={"uidb64": uid, "token": token})
    )

    subject = "Activa tu cuenta en MatchPlay"
    message = f"""
                Hola {user.first_name or user.username},

                Gracias por registrarte en MatchPlay ⚽🏆

                Para activar tu cuenta, haz clic en el siguiente enlace:

                {activation_link}

                Si no creaste esta cuenta, puedes ignorar este mensaje.
                """

    user.email_user(subject, message)

UserModel = get_user_model()
def activar_cuenta(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = UserModel.objects.get(pk=uid)
    except Exception:
        user = None

    if user and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()

        messages.success(request, "Tu cuenta ha sido verificada. Ahora puedes iniciar sesión 🎉")
        return redirect("login")

    messages.error(request, "El enlace de activación no es válido o ya fue usado.")
    return redirect("login")
