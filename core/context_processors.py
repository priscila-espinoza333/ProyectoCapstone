# core/context_processors.py
from core.models import Carrito  # ajusta el import si tu modelo está en otro lugar

def cart(request):
    """
    Expone 'cart_count' en todas las plantillas.
    Cuenta ítems del carrito ABIERTO (pagado=False) del usuario autenticado.
    """
    user = getattr(request, "user", None)
    count = 0

    if user and user.is_authenticated:
        carrito = (
            Carrito.objects
            .filter(usuario=user, pagado=False)   # <--- AQUÍ: pagado, no pagada
            .order_by("-id")
            .only("id")
            .first()
        )
        if carrito:
            # Ajusta 'reservas' si tu related_name es otro
            count = carrito.reservas.count()

    return {"cart_count": count}
