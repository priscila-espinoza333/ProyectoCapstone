
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings 
from transbank.webpay.webpay_plus.transaction import Transaction
from .models  import Carrito, ReservaTemporal, Cancha
from .services.reservas import crear_reserva_en_carrito, limpiar_reservas_expiradas
from django.contrib.auth.decorators import login_required


# -----------------------------
# FLUJO DE CARRITO Y PAGO
# -----------------------------
@login_required
def obtener_carrito(request):
    carrito, created = Carrito.objects.get_or_create(usuario=request.user, pagado = False)
    return carrito

@login_required
def agregar_reserva(request, cancha_id):
    cancha = get_object_or_404(Cancha, id=cancha_id)
    carrito = obtener_carrito(request)
    crear_reserva_en_carrito(carrito,  cancha)
    return redirect("Ver_carrito")


@login_required
def ver_carrito(request):
    carrito = obtener_carrito(request)
    for r in carrito.reserva.all():
        if r.esta_expirada():
            r.delete()
    carrito.refresh_from_db()
    return render(request, "core/reservas/carrito.html", {"carrito": carrito})

@login_required
def iniciar_pago_carrito(request, carrito_id):
    carrito = get_object_or_404(Carrito, id=carrito_id, usuario=request.user, pagado=False)
    
    #validar expiraciones de reservas antes de generar pago
    for reserva in carrito.reserva.all():
        if reserva.esta_expirada(): #limpiamos todo el carrito
            carrito.reserva.all().delete() 
            carrito.delete()
            return render(request, "core/reservas/pago_fallido.html", {"error": "Alguna reserva expiro. Vuelva a seleccionar horarios."})
    
    tx = Transaction()
    response = tx.create(
        buy_order=str(carrito.id),
        session_id=str(request.user.id),
        amount=float(carrito.total()),
        return_url=request.build_absolute_uri("/core/reservas/confirmar_pago_carrito/")  # URL absoluta
    )
    
    # volvemos a redirigir al formulario webpay
    return redirect(response['url'] + "?token_ws=" + response['token'])

@login_required
def confirmar_pago_carrito(request):
    token = request.GET.get("toke_ws")
    tx = Transaction()
    response = tx.commit(token)
    
    
    #buy_order es el id del carrito
    carrito = get_object_or_404(Carrito, id=response['buy_order'])
    
    
    if response.get('status') in ('AUTHORIZED', 'AUTHORIZED_TO_CAPTURE', 'APPROVED',):  # estados seguros
        carrito.pagado = True
        carrito.save()
        for reserva in carrito.reservas.all():
            reserva.pagada = True
            reserva.save()
        # Enviar email de confirmación (ver sección mail abajo)
        # enviar_confirmacion_pago(carrito)  # implementa según tu mail service
        return render(request, "core/reservas/pago_exitoso.html", {"carrito": carrito})
    else:
        #liberar reserva si pago falla
        carrito.reservas.all().delete()
        carrito.delete()
        return render(request, "core/reservas/pago_fallido.html", {"error": "El pago no fue autorizado."})