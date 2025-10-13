# core/views_errors.py
from django.shortcuts import render

def csrf_failure(request, reason=""):
    """
    Vista personalizada para manejar errores de verificación CSRF.
    """
    context = {
        "reason": reason,
        "title": "Sesión expirada",
        "message": (
            "Por seguridad, tu sesión ha expirado o el formulario ya no es válido. "
            "Por favor, actualiza la página e inténtalo nuevamente."
        ),
    }
    return render(request, "core/errors/csrf_failure.html", context, status=403)
