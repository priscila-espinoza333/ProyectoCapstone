# core/urls.py
from django.urls import path
from core import views

urlpatterns = [
    
    path("", views.index, name="index"),

    # listado dinámico (general o por deporte)
    path("canchas/", views.canchas, name="canchas"),
    path("canchas/<str:deporte>/", views.canchas, name="canchas_por_deporte"),
    path("canchas/categorias/", views.canchas_categorias, name="canchas_categorias"),


    # -----------------------------
    # FLUJO DE RESERVAS
    # -----------------------------
    path("canchas/<int:pk>/", views.cancha_detalle, name="cancha_detalle"),
    path("canchas/<int:cancha_id>/reservar/", views.reserva_crear, name="reserva_crear"),
    path("reservas/<int:reserva_id>/resumen/", views.reservas_resumen, name="reservas_resumen"),
    path("reservas/<int:reserva_id>/confirmar/", views.reservas_confirmar, name="reservas_confirmar"),
    path("reservas/<int:reserva_id>/exito/", views.reservas_exito, name="reservas_exito"),
    path("mis-reservas/", views.mis_reservas, name="mis_reservas"),
    path("reservas/<int:reserva_id>/cancelar/", views.reservas_cancelar, name="reservas_cancelar"),

]
