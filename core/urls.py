from django.contrib import admin
from django.urls import path
from core import views

urlpatterns = [
    
    path("admin/", admin.site.urls),
    path("", views.index, name="index"),
    
     # listado dinámico (general o por deporte)
    path("canchas/", views.canchas, name="canchas"),
    path("canchas/<int:pk>/", views.cancha_detalle, name="cancha_detalle"),
    path("canchas/deporte/<slug:deporte>/", views.canchas, name="canchas_por_deporte"),


    # -----------------------------
    # FLUJO DE RESERVAS
    # -----------------------------
    path("canchas/<int:pk>/", views.cancha_detalle, name="cancha_detalle"),
    path("canchas/deporte/<slug:deporte>/", views.canchas, name="canchas_por_deporte"),
    path("canchas/<int:cancha_id>/reservar/", views.reserva_crear, name="reserva_crear"),
    path("reservas/<int:reserva_id>/resumen/", views.reservas_resumen, name="reservas_resumen"),
    path("reservas/<int:reserva_id>/confirmar/", views.reservas_confirmar, name="reservas_confirmar"),
    path("reservas/<int:reserva_id>/exito/", views.reservas_exito, name="reservas_exito"),
    path("mis-reservas/", views.mis_reservas, name="mis_reservas"),
    path("reservas/<int:reserva_id>/cancelar/", views.reservas_cancelar, name="reservas_cancelar"),

    path("signup/", views.signup, name="signup"),

]
