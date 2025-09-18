from django.contrib import admin
from core.models import Recinto, Cancha, Reserva

@admin.register(Recinto)
class RecintoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "comuna", "telefono", "hora_apertura", "hora_cierre", "activo")
    list_filter = ("activo", "comuna")
    search_fields = ("nombre", "direccion", "comuna")


@admin.register(Cancha)
class CanchaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "recinto", "deporte", "precio_hora", "duracion_tramo_min", "activa")
    list_filter = ("activa", "deporte", "recinto")
    search_fields = ("nombre", "recinto__nombre")


@admin.action(description="Confirmar reservas seleccionadas")
def confirmar_reservas(modeladmin, request, queryset):
    queryset.filter(estado=Reserva.Estado.PENDIENTE).update(estado=Reserva.Estado.CONFIRMADA)

@admin.action(description="Cancelar reservas seleccionadas")
def cancelar_reservas(modeladmin, request, queryset):
    queryset.exclude(estado=Reserva.Estado.CANCELADA).update(estado=Reserva.Estado.CANCELADA)

@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ("cancha", "fecha_hora_inicio", "fecha_hora_fin", "estado", "precio_total", "email_contacto")
    list_filter = ("estado", "cancha__recinto", "cancha__deporte")
    search_fields = ("cancha__nombre", "email_contacto", "nombre_contacto", "telefono_contacto")
    actions = (confirmar_reservas, cancelar_reservas)
