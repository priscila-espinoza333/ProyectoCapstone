from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.template.loader import render_to_string
from django.utils.html import strip_tags

def enviar_correo_reserva(reserva):
    """
    Envía un comprobante de la reserva ya pagada al cliente.
    """
    destino = reserva.email_contacto or getattr(reserva.usuario, "email", None)
    if not destino:
        return

    cancha = reserva.cancha
    recinto = cancha.recinto

    inicio_local = timezone.localtime(reserva.fecha_hora_inicio)
    fin_local = timezone.localtime(reserva.fecha_hora_fin)

    # Link a Google Maps:
    map_link_url = getattr(recinto, "url_maps", "") or None
    if not map_link_url and getattr(cancha, "latitud", None) and getattr(cancha, "longitud", None):
        # Fallback con lat/long si no tienes url_maps
        map_link_url = (
            f"https://www.google.com/maps/search/?api=1"
            f"&query={cancha.latitud},{cancha.longitud}"
        )

    # Si algún día quieres usar Static Maps, podrías construir map_image_url aquí.
    map_image_url = None  # por ahora no usamos imagen dinámica

    subject = f"Comprobante de reserva #{reserva.id} - {recinto.nombre}"

    contexto = {
        "reserva_id": reserva.id,
        "nombre_usuario": (
            getattr(reserva.usuario, "get_full_name", lambda: "")()
            or getattr(reserva.usuario, "username", "")
        ),
        "recinto": recinto,
        "cancha": cancha,
        "deporte": cancha.get_deporte_display(),
        "fecha": inicio_local.strftime("%d/%m/%Y"),
        "hora_inicio": inicio_local.strftime("%H:%M"),
        "hora_fin": fin_local.strftime("%H:%M"),
        "estado_display": reserva.get_estado_display(),
        "total": f"{reserva.precio_total:,.0f}".replace(",", "."),
        "year": timezone.now().year,
        "soporte_email": getattr(settings, "SUPPORT_EMAIL", None),
        "map_link_url": map_link_url,
        "map_image_url": map_image_url,
    }

    html_message = render_to_string("core/emails/reserva_comprobante.html", contexto)
    plain_message = strip_tags(html_message)

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", settings.EMAIL_HOST_USER)

    send_mail(
        subject,
        plain_message,
        from_email,
        [destino],
        html_message=html_message,
        fail_silently=False,
    )
