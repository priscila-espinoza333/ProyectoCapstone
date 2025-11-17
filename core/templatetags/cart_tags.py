# core/templatetags/cart_tags.py
from django import template
from core.models import Carrito  # ajusta si está en otro módulo

register = template.Library()

@register.inclusion_tag("core/partials/_mini_cart_dropdown.html", takes_context=True)
def mini_cart_dropdown(context, limit=3):
    """
    Renderiza el ícono + dropdown del mini carrito.
    Usa el carrito ABIERTO (pagado=False) del usuario autenticado.
    """
    request = context.get("request")
    user = getattr(request, "user", None)

    carrito = None
    items = []
    total = 0
    count = 0

    if user and user.is_authenticated:
        carrito = (
            Carrito.objects
            .filter(usuario=user, pagado=False)   # <--- AQUÍ: pagado, no pagada
            .order_by("-id")
            .first()
        )
        if carrito:
            # related_name = 'reservas' en tu modelo Carrito
            qs = carrito.reservas.select_related("cancha").all()
            count = qs.count()
            items = list(qs[:limit])

            total = (
                carrito.obtener_total() if hasattr(carrito, "obtener_total")
                else getattr(carrito, "total", 0)
            ) or 0

    return {
        "carrito": carrito,
        "cart_items": items,
        "cart_count": count,
        "cart_total": total,
        "request": request,
        "limit": limit,
    }
