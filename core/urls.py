from django.contrib import admin
from django.urls import path
from core import views, views_cart
#rom . import views_cart

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
    path("reserva/<int:reserva_id>/pago/", views.pago_reserva, name="pago_reserva"),#----
    path("reserva/<int:reserva_id>/iniciar_pago/", views.iniciar_pago_reserva, name="iniciar_pago_reserva"),
    path("confirmar_pago_reserva/", views.confirmar_pago_reserva, name="confirmar_pago_reserva"),#-----
    path("reservas/<int:reserva_id>/confirmar/", views.reservas_confirmar, name="reservas_confirmar"),
    path("reservas/<int:reserva_id>/exito/", views.reservas_exito, name="reservas_exito"),
    path("mis-reservas/", views.mis_reservas, name="mis_reservas"),
    path("reservas/<int:reserva_id>/cancelar/", views.reservas_cancelar, name="reservas_cancelar"),

    path("signup/", views.signup, name="signup"),

    # -----------------------------
    # FLUJO DE CARRITO Y PAGO
    # -----------------------------

    path("carrito/", views_cart.ver_carrito, name="ver_carrito"),
    path("carrito/agregar/<int:cancha_id>/", views_cart.agregar_reserva, name="agregar_reserva"),
    path("carrito/pago/<int:carrito_id>/", views_cart.iniciar_pago_carrito, name="iniciar_pago_carrito"),
    path("confirmar_pago_carrito/", views_cart.confirmar_pago_carrito, name="confirmar_pago_carrito"),
]
