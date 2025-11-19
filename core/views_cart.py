# core/views_cart.py
from datetime import datetime
import json
from django.contrib import messages
import mercadopago
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.common.integration_type import IntegrationType
from django.db import transaction
from transbank.common.options import WebpayOptions

import uuid

from transbank.webpay.webpay_plus.transaction import Transaction
from core.models import Carrito, ReservaTemporal, Reserva, Cancha
from core.emails import enviar_correo_reserva


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
def agregar_reserva(request, cancha_id):
    """
    Agrega al carrito una ReservaTemporal con inicio/fin recibidos por POST.
    Si viene por GET (post-login), redirige sin error 405.
    """

    # Si llega por GET → pasa cuando el usuario volvió del login
    if request.method != "POST":
        return redirect("canchas")  # <<<<< AQUÍ DEFINES DÓNDE REBOTAR

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

    # Validar horario del recinto (si existe)
    try:
        rec = cancha.recinto
        if hasattr(rec, "horario_valido"):
            mismo_dia = (inicio.date() == fin.date())
            if not (mismo_dia and rec.horario_valido(inicio, fin)):
                messages.error(request, "El rango seleccionado está fuera del horario del recinto.")
                return _back_to_cancha(request, cancha_id)
    except Exception:
        pass

    # Validar disponibilidad
    try:
        if hasattr(cancha, "tiene_disponibilidad") and not cancha.tiene_disponibilidad(inicio, fin):
            messages.error(request, "La cancha no está disponible en ese horario.")
            return _back_to_cancha(request, cancha_id)
    except Exception:
        pass

    carrito = _get_or_create_carrito(request.user)
    precio = cancha.calcular_precio(inicio, fin)

    # Adaptación a modelos
    campos = {f.name for f in ReservaTemporal._meta.get_fields()}
    data = {
        "carrito": carrito,
        "cancha": cancha,
        "precio": precio,
        "pagada": False,
        "usuario": request.user,
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

    # Crear reserva temporal
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


def _get_or_create_carrito(user):
    """
    Devuelve el carrito 'abierto' del usuario (pagado=False) o lo crea si no existe.
    """
    carrito, created = Carrito.objects.get_or_create(
        usuario=user,
        pagado=False,  # 👈 OJO: aquí es pagado, como en tu modelo
    )
    return carrito

#######################################################
#######################################################
#######################################################
#######################################################

def _tbk_options():
    """Crea las opciones correctas según el entorno."""
    if getattr(settings, "TBK_ENV", "TEST") == "LIVE":
        return WebpayOptions(
            commerce_code=settings.TBK_COMMERCE_CODE,
            api_key=settings.TBK_API_KEY,
            integration_type=IntegrationType.LIVE,
        )
    # Sandbox oficial
    return WebpayOptions(
        commerce_code="597055555532",
        api_key="579B532A7440BB0C",
        integration_type=IntegrationType.TEST,
    )

@login_required
def tbk_iniciar_pago(request, carrito_id):
    """
    Crea una transacción Webpay Plus en SANDBOX y redirige al formulario de TBK.
    """
    # 1) Obtener carrito y total
    carrito = get_object_or_404(Carrito, id=carrito_id, usuario=request.user)
    try:
        total = float(carrito.obtener_total() if hasattr(carrito, "obtener_total") else getattr(carrito, "total", 0))
    except Exception:
        total = 0.0

    if total <= 0:
        return render(request, "core/pagos/error.html", {"mensaje": "Monto 0: agrega ítems al carrito."})

    # 2) Identificadores exigidos por TBK (con límites)
    buy_order = f"ORD-{uuid.uuid4().hex[:12].upper()}"  # ≤ 26 chars
    session_id = str(request.user.id)                   # ≤ 61 chars
    return_url = request.build_absolute_uri(reverse("tbk_confirmar_pago"))

    # 3) Opciones SANDBOX obligatorias (NO MALL)
    options = WebpayOptions(
        commerce_code="597055555532",
        api_key="579B532A7440BB0C",
        integration_type=IntegrationType.TEST
    )

    # 4) Crear transacción
    try:
        tx = Transaction(options)
        resp = tx.create(
            buy_order=buy_order,
            session_id=session_id,
            amount=int(round(total)),  # CLP entero
            return_url=return_url,
        )
    except Exception as e:
        return render(request, "core/pagos/error.html", {
            "mensaje": "Error al crear transacción Webpay.",
            "detalle": str(e),
        })

    url_tbk = (resp or {}).get("url")
    token = (resp or {}).get("token")
    if not url_tbk or not token:
        return render(request, "core/pagos/error.html", {
            "mensaje": "Webpay no entregó URL o token.",
            "detalle": resp,
        })

    # 5) Formulario auto-submit hacia TBK
    return render(request, "core/pagos/webpay_redirect.html", {
        "url_tbk": url_tbk,
        "token": token,
    })


@login_required
def tbk_confirmar_pago(request):
    """
    Commit de la transacción a la vuelta de Webpay.
    Si status = AUTHORIZED, puedes marcar el carrito como pagado.
    """
    token = request.POST.get("token_ws") or request.GET.get("token_ws")
    if not token:
        return render(request, "core/pagos/error.html", {"mensaje": "Falta token_ws de Webpay."})

    options = WebpayOptions(
        commerce_code="597055555532",
        api_key="579B532A7440BB0C",
        integration_type=IntegrationType.TEST
    )

    try:
        tx = Transaction(options)
        result = tx.commit(token)
    except Exception as e:
        return render(request, "core/pagos/error.html", {
            "mensaje": "Error al confirmar pago con Webpay.",
            "detalle": str(e),
        })

    status = (result or {}).get("status")

    if status == "AUTHORIZED":
        # TODO (opcional): si guardaste buy_order/session_id en tabla, aquí recuperas el carrito exacto
        # y lo marcas como pagado. Por ahora solo mostramos success.
        return render(request, "core/pagos/success.html", {
            "gateway": "Webpay",
            "result": result
        })

    # Otros estados: FAILED, REVERSED, etc.
    return render(request, "core/pagos/failure.html", {
        "gateway": "Webpay",
        "result": result
    })


@login_required
def iniciar_pago_carrito(request, carrito_id):
    """
    Alias legacy: algunas plantillas aún llaman a 'iniciar_pago_carrito'.
    Redirigimos a la pasarela por defecto (elige una).
    """
    # Opción A: Webpay como flujo por defecto
    return redirect('tbk_iniciar_pago', carrito_id=carrito_id)

    # Opción B (si prefieres Mercado Pago como default):
    # return redirect('mp_iniciar_pago', carrito_id=carrito_id)

#######################################################
#######################################################
#######################################################
#######################################################
#######################################################

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


############################################################################################
#####################################################
#######################################################
#################################################
@login_required
def mp_iniciar_pago(request, carrito_id):
    # 0) Token
    access_token = (getattr(settings, "MERCADOPAGO_ACCESS_TOKEN", "") or "").strip()
    if not access_token:
        return render(request, "core/pagos/error.html", {
            "mensaje": "Mercado Pago no está configurado (ACCESS_TOKEN vacío).",
            "detalle": {}
        })

    # 1) Carrito y total
    carrito = get_object_or_404(Carrito, id=carrito_id, usuario=request.user)
    total_raw = carrito.obtener_total() if hasattr(carrito, "obtener_total") else getattr(carrito, "total", 0)
    try:
        total = float(total_raw or 0)
    except Exception:
        total = 0.0
    if total <= 0:
        return render(request, "core/pagos/error.html", {
            "mensaje": "Monto 0: agrega ítems al carrito.",
            "detalle": {"total": total_raw}
        })
    total = round(total, 2)

    # 2) SDK
    sdk = mercadopago.SDK(access_token)

    # 3) URLs
    success_url = getattr(settings, "MERCADOPAGO_SUCCESS_URL", request.build_absolute_uri(reverse("mp_success")))
    failure_url = getattr(settings, "MERCADOPAGO_FAILURE_URL", request.build_absolute_uri(reverse("mp_failure")))
    pending_url = getattr(settings, "MERCADOPAGO_PENDING_URL", request.build_absolute_uri(reverse("mp_pending")))

    # 4) Identificadores
    external_ref = f"MP-{carrito.id}-{uuid.uuid4().hex[:8]}"

    # 5) Emails de prueba
    buyer_email = (getattr(settings, "MERCADOPAGO_TEST_BUYER_EMAIL", "") or "").strip()
    seller_email = (getattr(settings, "MERCADOPAGO_TEST_SELLER_EMAIL", "") or "").strip()
    if seller_email and buyer_email and buyer_email.lower() == seller_email.lower():
        # Evita el clásico "Invalid users involved"
        return render(request, "core/pagos/error.html", {
            "mensaje": "Buyer y Seller no pueden ser el mismo usuario (emails iguales).",
            "detalle": {"buyer_email": buyer_email, "seller_email": seller_email}
        })

    # 6) Preferencia mínima y amigable
    preference_data = {
        "items": [{
            "title": f"MatchPlay - Carrito #{carrito.id}",
            "quantity": 1,
            "unit_price": total,
            "currency_id": "CLP",
        }],
        "back_urls": {
            "success": success_url,
            "failure": failure_url,
            "pending": pending_url,
        },
        ##"auto_return": "approved",
        "payer": {
            "email": buyer_email or "test_user_123456@testuser.com"  # fuerza comprador de prueba
        },
        # Evita boletos/cupones y reduce validaciones
        "payment_methods": {
            "excluded_payment_types": [{"id": "ticket"}]
        },
        # Identificador útil para reconciliar
        "external_reference": external_ref,
        # Texto en el extracto (donde aplique)
        "statement_descriptor": "MATCHPLAY",
        # ⚠️ No uses webhook en localhost hasta que funcione el flujo básico:
        # "notification_url": getattr(settings, "MERCADOPAGO_WEBHOOK_URL", ""),
        # "purpose": "wallet_purchase",  # si te da problemas, quítalo
    }

    # 7) Crear preferencia
    try:
        preference = sdk.preference().create(preference_data)
    except Exception as e:
        return render(request, "core/pagos/error.html", {
            "mensaje": "Excepción del SDK al crear preferencia.",
            "detalle": {"exception": str(e), "preference_data": preference_data}
        })

    # 8) Normaliza respuesta
    resp = preference.get("response") or preference.get("body") or preference

    # 9) Si hay error, muéstralo completo en pantalla (debug claro)
    if isinstance(resp, dict) and (resp.get("error") or resp.get("message") or resp.get("cause")):
        # Pretty print JSON en la plantilla
        return render(request, "core/pagos/error.html", {
            "mensaje": "Mercado Pago rechazó la preferencia.",
            "detalle": json.dumps(resp, ensure_ascii=False, indent=2)
        })

    # 10) Redirección al checkout 
    init_point = None
    if isinstance(resp, dict):
        init_point = resp.get("init_point") or resp.get("sandbox_init_point")

    if not init_point:
        return render(request, "core/pagos/error.html", {
            "mensaje": "Mercado Pago no entregó init_point.",
            "detalle": json.dumps(resp or preference or {"preference_data": preference_data}, ensure_ascii=False, indent=2)
        })

    return redirect(init_point)

##########################################
##########################################
########################################################
##########################################

@login_required
def mp_success(request):
    # Aquí marcas pagado si quieres confiar en el redirect + query params
    # Recomendado: esperar webhook para estado final.
    return render(request, "core/pagos/exito.html", {"resultado": dict(request.GET)})

@login_required
def mp_failure(request):
    return render(request, "core/pagos/error.html", {"mensaje": "Pago fallido", "detalle": dict(request.GET)})

@login_required
def mp_pending(request):
    return render(request, "core/pagos/pending.html", {"detalle": dict(request.GET)})

@csrf_exempt
def mp_webhook(request):
    """
    Recibe notificaciones de Mercado Pago.
    Aquí consultas el payment/status por ID y, si está aprobado,
    marcas el carrito/reservas como pagadas y cierras el carrito.
    """
    # Puedes loguear request.body y luego consultar al SDK:
    # payment_info = sdk.payment().get(payment_id)
    return render(request, "core/pagos/ok.html")  # 200 OK


@login_required
@transaction.atomic
def dummy_pagar_carrito(request, carrito_id):
    # 1. Obtener el carrito del usuario, que aún no esté pagado
    carrito = get_object_or_404(
        Carrito,
        id=carrito_id,
        usuario=request.user,
        pagado=False,
    )

    # 2. Crear reservas definitivas desde las reservas temporales del carrito
    reservas_creadas = []
    for rt in carrito.reservas.filter(pagada=False):
        reserva = Reserva.objects.create(
            cancha=rt.cancha,
            usuario=request.user,
            nombre_contacto=getattr(request.user, "get_full_name", lambda: "")() or request.user.username,
            email_contacto=getattr(request.user, "email", ""),
            telefono_contacto="",  # si tienes teléfono lo agregas acá
            fecha_hora_inicio=rt.hora_inicio,
            fecha_hora_fin=rt.hora_fin,
            precio_total=rt.precio,
            estado=Reserva.Estado.CONFIRMADA,
        )
        reservas_creadas.append(reserva)
        # marcar la reserva temporal como pagada (opcional, pero prolijo)
        rt.pagada = True
        rt.save()

    # 3. Marcar el carrito como pagado
    carrito.pagado = True
    carrito.save()

    # 4. Enviar un correo por cada reserva creada
    for r in reservas_creadas:
        enviar_correo_reserva(r)

    # 5. Feedback al usuario
    messages.success(
        request,
        "Pago simulado realizado con éxito. Te enviamos el detalle de tu(s) reserva(s) por correo."
    )

    # Redirige donde prefieras: mis_reservas, resumen, etc.
    return redirect("mis_reservas")