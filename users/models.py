from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        CLIENTE = "CLIENTE", "Cliente"
        ADMIN_RECINTO = "ADMIN_RECINTO", "Admin de Recinto"
        SUPERADMIN = "SUPERADMIN", "Super Admin"

    rut = models.CharField(max_length=12, unique=True, null=True, blank=True)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    rol = models.CharField(max_length=20, choices=Role.choices, default=Role.CLIENTE)

    def __str__(self):
        return f"{self.username} ({self.rol})"
