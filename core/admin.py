from django.contrib import admin
from django.utils import timezone
from django.db.models import Sum

from core.models import Recinto, Cancha, Reserva, Carrito, ReservaTemporal


# ---------- Inlines ----------
class ReservaInline(admin.TabularInline):
    model = Reserva
    extra = 0
    fields = ("usuario", "fecha_hora_inicio", "fecha_hora_fin", "estado", "precio_total")
    readonly_fields = ("precio_total",)
    show_change_link = True

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("usuario")


# ---------- Recinto ----------
@admin.register(Recinto)
class RecintoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "comuna", "telefono", "activo", "hora_apertura", "hora_cierre")
    list_filter = ("activo", "comuna")
    search_fields = ("nombre", "direccion", "comuna", "telefono", "email")
    ordering = ("nombre",)
    readonly_fields = ("creado_en", "actualizado_en")


# ---------- Cancha ----------
@admin.register(Cancha)
class CanchaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "recinto", "deporte", "tipo_superficie", "precio_hora", "activa")
    list_filter = ("activa", "deporte", "recinto")
    search_fields = ("nombre", "recinto__nombre", "tipo_superficie")
    ordering = ("recinto__nombre", "nombre")
    autocomplete_fields = ("recinto",)
    readonly_fields = ("creado_en", "actualizado_en")
    inlines = [ReservaInline]
    list_select_related = ("recinto",)


# ---------- Acciones Reserva ----------
@admin.action(description="Marcar seleccionadas como CONFIRMADAS")
def marcar_confirmadas(modeladmin, request, queryset):
    updated = queryset.update(estado=Reserva.Estado.CONFIRMADA)
    modeladmin.message_user(request, f"{updated} reserva(s) marcadas como confirmadas.")

@admin.action(description="Marcar seleccionadas como CANCELADAS")
def marcar_canceladas(modeladmin, request, queryset):
    updated = queryset.update(estado=Reserva.Estado.CANCELADA)
    modeladmin.message_user(request, f"{updated} reserva(s) marcadas como canceladas.")


# ---------- Reserva ----------
@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = (
        "id", "cancha", "recinto_nombre", "usuario",
        "fecha_hora_inicio", "fecha_hora_fin", "estado", "precio_total",
    )
    list_filter = ("estado", "cancha__recinto", "cancha__deporte")
    search_fields = ("usuario__username", "usuario__email", "nombre_contacto", "email_contacto", "telefono_contacto")
    ordering = ("-fecha_hora_inicio",)
    autocomplete_fields = ("cancha", "usuario")
    readonly_fields = ("creado_en", "actualizado_en", "precio_total")
    date_hierarchy = "fecha_hora_inicio"
    list_select_related = ("cancha", "cancha__recinto", "usuario")
    actions = [marcar_confirmadas, marcar_canceladas]

    fieldsets = (
        ("Datos de la reserva", {
            "fields": (
                ("cancha", "usuario"),
                ("fecha_hora_inicio", "fecha_hora_fin"),
                ("estado", "precio_total"),
            )
        }),
        ("Contacto", {
            "fields": (("nombre_contacto", "email_contacto", "telefono_contacto"),),
            "classes": ("collapse",),
        }),
        ("Metadatos", {
            "fields": (("creado_en", "actualizado_en"),),
            "classes": ("collapse",),
        }),
    )

    @admin.display(ordering="cancha__recinto__nombre", description="Recinto")
    def recinto_nombre(self, obj):
        return obj.cancha.recinto.nombre


# ---------- Carrito ----------
@admin.register(Carrito)
class CarritoAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario", "pagado", "creado_en", "total_decimal")
    list_filter = ("pagado",)
    search_fields = ("usuario__username", "usuario__email")
    autocomplete_fields = ("usuario",)
    readonly_fields = ("creado_en",)
    date_hierarchy = "creado_en"
    list_select_related = ("usuario",)

    @admin.display(description="Total")
    def total_decimal(self, obj):
        # usa tu propiedad total (Decimal)
        return obj.total

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("usuario")


# ---------- Acciones ReservaTemporal ----------
@admin.action(description="Eliminar reservas temporales expiradas (no pagadas)")
def eliminar_expiradas(modeladmin, request, queryset):
    ahora = timezone.now()
    to_delete = queryset.filter(pagada=False, expira_en__lt=ahora)
    n = to_delete.count()
    to_delete.delete()
    modeladmin.message_user(request, f"Eliminadas {n} reserva(s) temporales expiradas.")

@admin.action(description="Marcar seleccionadas como pagadas")
def marcar_temporales_pagadas(modeladmin, request, queryset):
    n = queryset.update(pagada=True)
    modeladmin.message_user(request, f"{n} reserva(s) temporales marcadas como pagadas.")


# ---------- ReservaTemporal ----------
@admin.register(ReservaTemporal)
class ReservaTemporalAdmin(admin.ModelAdmin):
    list_display = ("id", "carrito", "usuario_nombre", "cancha", "hora_inicio", "hora_fin", "precio", "pagada", "expira_en")
    list_filter = ("pagada", "carrito__usuario", "cancha__recinto")
    search_fields = ("carrito__usuario__username", "carrito__usuario__email", "cancha__nombre")
    autocomplete_fields = ("carrito", "cancha")
    date_hierarchy = "hora_inicio"
    list_select_related = ("carrito", "carrito__usuario", "cancha", "cancha__recinto")
    actions = [eliminar_expiradas, marcar_temporales_pagadas]

    @admin.display(description="Usuario")
    def usuario_nombre(self, obj):
        u = obj.carrito.usuario
        return getattr(u, "username", None) or getattr(u, "email", None) or f"id={obj.carrito.usuario_id}"
