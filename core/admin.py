from django.contrib import admin
from core.models import Recinto, Cancha, Reserva

class ReservaInline(admin.TabularInline):
    model = Reserva
    extra = 0
    fields = ("usuario", "fecha_hora_inicio", "fecha_hora_fin", "estado", "precio_total")
    readonly_fields = ("precio_total",)
    show_change_link = True


@admin.register(Recinto)
class RecintoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "comuna", "telefono", "activo", "hora_apertura", "hora_cierre")
    list_filter = ("activo", "comuna")
    search_fields = ("nombre", "direccion", "comuna", "telefono", "email")
    ordering = ("nombre",)
    readonly_fields = ("creado_en", "actualizado_en")


@admin.register(Cancha)
class CanchaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "recinto", "deporte", "tipo_superficie", "precio_hora", "activa")
    list_filter = ("activa", "deporte", "recinto")
    search_fields = ("nombre", "recinto__nombre", "tipo_superficie")
    ordering = ("recinto__nombre", "nombre")
    autocomplete_fields = ("recinto",)
    readonly_fields = ("creado_en", "actualizado_en")
    inlines = [ReservaInline]


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ("cancha", "usuario", "fecha_hora_inicio", "fecha_hora_fin", "estado", "precio_total")
    list_filter = ("estado", "cancha__recinto", "cancha__deporte")
    search_fields = ("usuario__username", "nombre_contacto", "email_contacto", "telefono_contacto")
    ordering = ("-fecha_hora_inicio",)
    autocomplete_fields = ("cancha", "usuario")
    readonly_fields = ("creado_en", "actualizado_en", "precio_total")
    date_hierarchy = "fecha_hora_inicio"
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

