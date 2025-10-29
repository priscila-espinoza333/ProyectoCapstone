# core/models.py
from decimal import Decimal
from datetime import time, datetime, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Sum
from django.utils import timezone


# ---------- helpers ----------
def default_expiry():
    """Hold de 5 minutos para las reservas temporales."""
    return timezone.now() + timedelta(minutes=5)


# ---------- dominio ----------
class Recinto(models.Model):
    nombre = models.CharField(max_length=120)
    direccion = models.CharField(max_length=255, blank=True)
    comuna = models.CharField(max_length=120, blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    url_maps = models.URLField(blank=True)

    hora_apertura = models.TimeField(default=time(8, 0))   # 08:00
    hora_cierre = models.TimeField(default=time(23, 0))    # 23:00
    activo = models.BooleanField(default=True)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Recinto"
        verbose_name_plural = "Recintos"
        ordering = ("nombre",)

    def __str__(self):
        return self.nombre

    def horario_valido(self, inicio_dt: datetime, fin_dt: datetime) -> bool:
        # Normaliza a hora local si son “aware”
        if timezone.is_aware(inicio_dt):
            inicio_dt = timezone.localtime(inicio_dt)
        if timezone.is_aware(fin_dt):
            fin_dt = timezone.localtime(fin_dt)

        if inicio_dt.date() != fin_dt.date():
            return False
        hi = inicio_dt.time()
        hf = fin_dt.time()
        return (self.hora_apertura <= hi < self.hora_cierre) and (self.hora_apertura < hf <= self.hora_cierre)


class Cancha(models.Model):
    class Deporte(models.TextChoices):
        FUTBOL = "FUTBOL", "Fútbol"
        TENIS = "TENIS", "Tenis"
        PADEL = "PADEL", "Pádel"
        MULTI = "MULTI", "Multicancha"
        OTRO = "OTRO", "Otro"

    recinto = models.ForeignKey(Recinto, on_delete=models.CASCADE, related_name="canchas")
    nombre = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True)
    deporte = models.CharField(max_length=12, choices=Deporte.choices, default=Deporte.FUTBOL)
    tipo_superficie = models.CharField(max_length=60, blank=True)

    # Precio por hora
    precio_hora = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )
    duracion_tramo_min = models.PositiveIntegerField(
        default=60, validators=[MinValueValidator(15), MaxValueValidator(240)]
    )
    activa = models.BooleanField(default=True)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cancha"
        verbose_name_plural = "Canchas"
        unique_together = (("recinto", "nombre"),)
        ordering = ("recinto__nombre", "nombre")

    def __str__(self):
        return f"{self.recinto.nombre} - {self.nombre}"

    def tiene_disponibilidad(self, inicio: datetime, fin: datetime) -> bool:
        # Import diferido para usar la constante Estado sin cargarla antes de tiempo
        from .models import Reserva
        return not self.reservas.filter(
            estado__in=[Reserva.Estado.PENDIENTE, Reserva.Estado.CONFIRMADA],
            fecha_hora_inicio__lt=fin,
            fecha_hora_fin__gt=inicio,
        ).exists()

    def calcular_precio(self, inicio: datetime, fin: datetime) -> Decimal:
        """Calcula precio prorrateado en horas usando Decimal (sin floats)."""
        seconds = Decimal((fin - inicio).total_seconds())
        hours = seconds / Decimal(3600)
        # Si quieres forzar 2 decimales exactos: return (self.precio_hora * hours).quantize(Decimal("0.01"))
        return self.precio_hora * hours

    def proponer_fin(self, inicio: datetime, duracion_min: int | None = None) -> datetime:
        if duracion_min is None:
            duracion_min = self.duracion_tramo_min
        return inicio + timedelta(minutes=duracion_min)


class Reserva(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        CONFIRMADA = "CONFIRMADA", "Confirmada"
        CANCELADA = "CANCELADA", "Cancelada"
        NO_SHOW = "NO_SHOW", "No show"

    cancha = models.ForeignKey(Cancha, on_delete=models.PROTECT, related_name="reservas")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reservas"
    )
    nombre_contacto = models.CharField(max_length=120, blank=True)
    email_contacto = models.EmailField(blank=True)
    telefono_contacto = models.CharField(max_length=30, blank=True)

    fecha_hora_inicio = models.DateTimeField()
    fecha_hora_fin = models.DateTimeField()
    precio_total = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDIENTE)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Reserva"
        verbose_name_plural = "Reservas"
        ordering = ("-fecha_hora_inicio",)
        indexes = [
            models.Index(fields=["cancha", "fecha_hora_inicio"]),
            models.Index(fields=["cancha", "fecha_hora_fin"]),
            models.Index(fields=["estado"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(fecha_hora_fin__gt=models.F("fecha_hora_inicio")),
                name="reserva_fin_mayor_que_inicio",
            ),
        ]

    def __str__(self):
        return f"{self.cancha} | {self.fecha_hora_inicio:%Y-%m-%d %H:%M} → {self.fecha_hora_fin:%H:%M} [{self.estado}]"

    def clean(self):
        super().clean()
        if self.fecha_hora_inicio and self.fecha_hora_fin:
            if self.fecha_hora_inicio >= self.fecha_hora_fin:
                raise ValidationError("La hora de fin debe ser posterior al inicio.")
            if self.fecha_hora_inicio < timezone.now():
                raise ValidationError("No puedes reservar en el pasado.")
            rec: Recinto = self.cancha.recinto
            if not rec.horario_valido(self.fecha_hora_inicio, self.fecha_hora_fin):
                raise ValidationError("El horario solicitado está fuera del horario del recinto.")
            if self.estado in (self.Estado.PENDIENTE, self.Estado.CONFIRMADA):
                solapa = self.cancha.reservas.exclude(pk=self.pk).filter(
                    estado__in=[self.Estado.PENDIENTE, self.Estado.CONFIRMADA],
                    fecha_hora_inicio__lt=self.fecha_hora_fin,
                    fecha_hora_fin__gt=self.fecha_hora_inicio,
                ).exists()
                if solapa:
                    raise ValidationError("La cancha no está disponible en ese horario.")

    def save(self, *args, **kwargs):
        self.full_clean()
        if not self.precio_total and self.cancha_id and self.fecha_hora_inicio and self.fecha_hora_fin:
            self.precio_total = self.cancha.calcular_precio(self.fecha_hora_inicio, self.fecha_hora_fin)
        return super().save(*args, **kwargs)

    @property
    def fecha(self):
        return timezone.localtime(self.fecha_hora_inicio).date() if timezone.is_aware(self.fecha_hora_inicio) else self.fecha_hora_inicio.date()

    @property
    def hora_inicio(self):
        return timezone.localtime(self.fecha_hora_inicio).time() if timezone.is_aware(self.fecha_hora_inicio) else self.fecha_hora_inicio.time()

    @property
    def hora_fin(self):
        return timezone.localtime(self.fecha_hora_fin).time() if timezone.is_aware(self.fecha_hora_fin) else self.fecha_hora_fin.time()


class Carrito(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="carritos",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    pagado = models.BooleanField(default=False)

    class Meta:
        ordering = ("-creado_en",)
        verbose_name = "Carrito"
        verbose_name_plural = "Carritos"
        indexes = [
            models.Index(fields=["usuario", "pagado"]),
        ]

    @property
    def total(self) -> Decimal:
        """Suma segura con Decimal de todas las reservas temporales del carrito."""
        agg = self.reservas.aggregate(suma=Sum("precio"))
        return agg["suma"] or Decimal("0.00")

    def __str__(self):
        nombre = getattr(self.usuario, "username", None) or getattr(self.usuario, "email", None) or f"id={self.usuario_id}"
        return f"Carrito {self.id} = {nombre}"


class ReservaTemporal(models.Model):
    carrito = models.ForeignKey(
        "core.Carrito",
        related_name="reservas",
        on_delete=models.CASCADE
    )
    cancha = models.ForeignKey("core.Cancha", on_delete=models.CASCADE)

    # ➜ nuevo: alinea el modelo con la columna ya existente en la BD
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reservas_temporales",
        db_column="usuario_id",   # importante: usa la columna física existente
    )

    hora_inicio = models.DateTimeField()
    hora_fin = models.DateTimeField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    pagada = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)
    expira_en = models.DateTimeField(default=default_expiry)

    class Meta:
        ordering = ("-creado_en",)
        indexes = [
            models.Index(fields=["carrito", "pagada"]),
            models.Index(fields=["expira_en"]),
            # (opcional) acelera consultas por usuario:
            # models.Index(fields=["usuario"]),
        ]
        verbose_name = "Reserva temporal"
        verbose_name_plural = "Reservas temporales"

    def save(self, *args, **kwargs):
        if self.expira_en is None:
            self.expira_en = default_expiry()
        super().save(*args, **kwargs)

    @property
    def duracion_minutos(self) -> int:
        return int((self.hora_fin - self.hora_inicio).total_seconds() // 60)

    def esta_expirada(self) -> bool:
        return (not self.pagada) and timezone.now() > self.expira_en

    def __str__(self):
        usuario = (
            getattr(self.carrito.usuario, "username", None)
            or getattr(self.carrito.usuario, "email", None)
            or f"id={self.carrito.usuario_id}"
        )
        return f"Reserva {self.id} = {self.cancha.nombre} ({usuario})"