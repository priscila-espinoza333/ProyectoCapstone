from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "rol", "is_active", "date_joined")
    list_filter = ("rol", "is_staff", "is_superuser", "is_active")
    search_fields = ("username", "email", "rut")
    fieldsets = UserAdmin.fieldsets + (
        ("Datos adicionales", {"fields": ("rut", "telefono", "rol")}),
    )
