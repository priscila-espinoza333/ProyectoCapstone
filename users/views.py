# users/views.py
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.conf import settings

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        remember_me = request.POST.get("remember_me") == "on"
        next_url = request.POST.get("next") or settings.LOGIN_REDIRECT_URL

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)

            if remember_me:
                # Persistente con renovación por actividad
                # (se apoya en SESSION_COOKIE_AGE y SESSION_SAVE_EVERY_REQUEST=True)
                request.session.set_expiry(settings.SESSION_COOKIE_AGE)
            else:
                # Cierra al cerrar el navegador
                request.session.set_expiry(0)

            return redirect(next_url)

        return render(request, "users/login.html", {"error": "Credenciales inválidas"})

    # GET
    return render(request, "users/login.html")
