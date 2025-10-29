# core/middleware.py
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from django.contrib.auth import logout

class AdminSessionHardeningMiddleware(MiddlewareMixin):
    """
    Endurece la sesión cuando el request apunta a /admin:
    - Expira al cerrar el navegador (sin fecha fija)
    - Autologout por inactividad (ej. 30 min)
    """
    ADMIN_IDLE_SECONDS = 30 * 60  # 30 minutos

    def process_request(self, request):
        # Asegura que el path exista y sea str
        path = getattr(request, "path", "") or ""
        if path.startswith("/admin"):
            # 1) Forzar expiración al cerrar navegador
            request.session.set_expiry(0)

            # 2) Autologout por inactividad
            if request.user.is_authenticated:
                last_seen = request.session.get("_admin_last_seen")
                now = timezone.now().timestamp()
                if last_seen and (now - last_seen) > self.ADMIN_IDLE_SECONDS:
                    logout(request)
                # Actualiza marca de tiempo en cada request a /admin
                request.session["_admin_last_seen"] = now
        return None
