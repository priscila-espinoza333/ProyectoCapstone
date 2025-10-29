# core/management/commands/generar_reservas_fake.py
import random
from decimal import Decimal
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Reserva, Cancha
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = (
        "Genera reservas de ejemplo. Por defecto crea SOLO FUTURO (respeta validaciones). "
        "Usa --historico para generar pasado+futuro con bulk_create (no valida pasado)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--cantidad",
            type=int,
            default=1000,
            help="Número de reservas a generar (default: 1000)",
        )
        parser.add_argument(
            "--solo_futuro",
            action="store_true",
            help="Fuerza generar SOLO reservas futuras (valida save/full_clean).",
        )
        parser.add_argument(
            "--historico",
            action="store_true",
            help="Genera datos PASADO+FUTURO usando bulk_create (omite validaciones).",
        )
        parser.add_argument(
            "--dias_futuro_max",
            type=int,
            default=60,
            help="Máximo de días hacia adelante para generar (default: 60).",
        )
        parser.add_argument(
            "--dias_pasado_max",
            type=int,
            default=90,
            help="Máximo de días hacia atrás cuando --historico (default: 90).",
        )

    def handle(self, *args, **opt):
        cantidad = opt["cantidad"]
        solo_futuro = opt["solo_futuro"]
        historico = opt["historico"]
        dias_futuro_max = max(0, opt["dias_futuro_max"])
        dias_pasado_max = max(0, opt["dias_pasado_max"])

        if historico and solo_futuro:
            self.stdout.write(self.style.WARNING(
                "Se pasó --historico y --solo_futuro juntos. Se usará --solo_futuro (valida reglas)."
            ))
            historico = False

        if not Cancha.objects.exists():
            self.stdout.write(self.style.ERROR(
                "⚠️ No hay canchas registradas. Crea algunas en /admin/core/cancha/ antes de ejecutar."
            ))
            return

        canchas = list(Cancha.objects.all())
        usuarios = list(User.objects.all())

        estados = [
            Reserva.Estado.PENDIENTE,
            Reserva.Estado.CONFIRMADA,
            Reserva.Estado.CANCELADA,
            Reserva.Estado.NO_SHOW,
        ]
        # Sesgos: 60% confirmadas, 20% pendientes, 10% canceladas, 10% no-show
        state_weights = [0.2, 0.6, 0.1, 0.1]

        ahora = timezone.now()

        # ------------ MODO SOLO FUTURO (respeta validaciones) ------------
        if solo_futuro or not historico:
            creadas = 0
            for i in range(cantidad):
                cancha = random.choice(canchas)
                usuario = random.choice(usuarios) if usuarios else None
                estado = random.choices(estados, weights=state_weights)[0]

                # Solo fechas futuras (evita romper "no reservar en el pasado")
                delta_dias = random.randint(0, max(1, dias_futuro_max))
                # Horario entre 08:00 y 22:00 en punto
                inicio = (ahora + timedelta(days=delta_dias)).replace(
                    hour=random.randint(8, 22), minute=0, second=0, microsecond=0
                )
                duracion_horas = random.choice([1, 2])  # 1h o 2h
                fin = inicio + timedelta(hours=duracion_horas)

                precio = Decimal(random.randint(10000, 25000))

                # Usa create() -> llama save() y full_clean()
                Reserva.objects.create(
                    cancha=cancha,
                    usuario=usuario,
                    nombre_contacto=f"Cliente {i}",
                    email_contacto=f"cliente{i}@example.com",
                    telefono_contacto=f"+569{random.randint(11111111, 99999999)}",
                    fecha_hora_inicio=inicio,
                    fecha_hora_fin=fin,
                    precio_total=precio,
                    estado=estado,
                )
                creadas += 1

            self.stdout.write(self.style.SUCCESS(
                f"✅ {creadas} reservas creadas (SOLO FUTURO, validaciones activas)."
            ))
            return

        # ------------ MODO HISTÓRICO (bulk_create, omite validaciones) ------------
        objs = []
        for i in range(cantidad):
            cancha = random.choice(canchas)
            usuario = random.choice(usuarios) if usuarios else None
            estado = random.choices(estados, weights=state_weights)[0]

            # Pasado (-dias_pasado_max .. -1), Presente (0), Futuro (1 .. dias_futuro_max)
            delta_dias = random.randint(-dias_pasado_max, dias_futuro_max)

            inicio = (ahora + timedelta(days=delta_dias)).replace(
                hour=random.randint(8, 22), minute=0, second=0, microsecond=0
            )
            fin = inicio + timedelta(hours=random.choice([1, 2]))

            precio = Decimal(random.randint(10000, 25000))

            # IMPORTANTE: bulk_create NO llama save()/full_clean() → respeta tu CheckConstraint fin>inicio
            objs.append(Reserva(
                cancha=cancha,
                usuario=usuario,
                nombre_contacto=f"Cliente {i}",
                email_contacto=f"cliente{i}@example.com",
                telefono_contacto=f"+569{random.randint(11111111, 99999999)}",
                fecha_hora_inicio=inicio,
                fecha_hora_fin=fin,
                precio_total=precio,
                estado=estado,
            ))

        Reserva.objects.bulk_create(objs, batch_size=500)
        self.stdout.write(self.style.SUCCESS(
            f"✅ {len(objs)} reservas insertadas (HISTÓRICO + FUTURO, bulk_create sin validaciones)."
        ))
