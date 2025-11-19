# core/templatetags/cart_tags.py
from django import template
from core.views_cart import _get_or_create_carrito  # 👈 IMPORTAMOS DESDE views_cart

register = template.Library()

@register.inclusion_tag("core/partials/_mini_cart_dropdown.html", takes_context=True)
def mini_cart_dropdown(context, limit=3):
    request = context["request"]

    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        # No mostrar nada si no hay usuario logueado
        return {}

    # Usamos la MISMA lógica que en las vistas
    carrito = _get_or_create_carrito(user)

    # Traemos reservas del carrito
    reservas_qs = carrito.reservas.select_related("cancha").order_by("-creado_en")
    items = list(reservas_qs[:limit])
    cart_count = reservas_qs.count()
    subtotal = sum(r.precio for r in reservas_qs)

    return {
        "items": items,
        "cart_count": cart_count,
        "subtotal": subtotal,
    }
