# core/models.py
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import time, datetime, timedelta


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

    # Fechas (sin default: auto_now* y default son excluyentes)
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

    precio_hora = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    duracion_tramo_min = models.PositiveIntegerField(default=60, validators=[MinValueValidator(15), MaxValueValidator(240)])
    activa = models.BooleanField(default=True)

    # Fechas
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
        from .models import Reserva
        return not self.reservas.filter(
            estado__in=[Reserva.Estado.PENDIENTE, Reserva.Estado.CONFIRMADA],
            fecha_hora_inicio__lt=fin,
            fecha_hora_fin__gt=inicio
        ).exists()

    def calcular_precio(self, inicio: datetime, fin: datetime) -> float:
        mins = (fin - inicio).total_seconds() / 60.0
        return float(self.precio_hora) * (mins / 60.0)

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
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reservas")
    nombre_contacto = models.CharField(max_length=120, blank=True)
    email_contacto = models.EmailField(blank=True)
    telefono_contacto = models.CharField(max_length=30, blank=True)

    fecha_hora_inicio = models.DateTimeField()
    fecha_hora_fin = models.DateTimeField()
    precio_total = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDIENTE)

    # Fechas
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
