# core/views_auth.py

from django.contrib.auth.views import PasswordResetConfirmView
from django.contrib.auth import logout
from django.shortcuts import redirect

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    """
    Vista de confirmación de reseteo de contraseña.
    - Cambia la contraseña usando form.save()
    - Limpia el token de sesión si existe
    - Cierra la sesión del usuario
    - Redirige al login
    """
    def form_valid(self, form):
        # 1) Cambia la contraseña del usuario
        user = form.save()

        # 2) Limpia el token de reset SOLO si existe (evitamos KeyError)
        try:
            # Nombre interno que usa Django para el token
            self.request.session.pop("_password_reset_token", None)
        except Exception:
            pass  # por seguridad, pero no debería explotar

        # 3) Cerramos cualquier sesión activa
        logout(self.request)

        # 4) Redirigimos al login
        return redirect("login")
