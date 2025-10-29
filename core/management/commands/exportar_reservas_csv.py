import csv
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils.timezone import localtime

from core.models import Reserva

class Command(BaseCommand):
    help = "Exporta la tabla Reserva a un CSV para BI (Looker Studio / Sheets)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            default="reservas_export.csv",
            help="Ruta/nombre del CSV de salida (default: reservas_export.csv)",
        )
        parser.add_argument(
            "--delimiter",
            type=str,
            default=",",
            help="Delimitador CSV (default: ,)",
        )

    def handle(self, *args, **opts):
        output = opts["output"]
        delimiter = opts["delimiter"]

        # Columnas a exportar (ajusta si quieres más)
        headers = ["fecha_hora_inicio", "fecha_hora_fin", "precio_total", "estado"]

        # iterator() evita cargar todo en memoria si hay muchas filas
        qs = (Reserva.objects
              .only("fecha_hora_inicio", "fecha_hora_fin", "precio_total", "estado")
              .order_by("fecha_hora_inicio")
              .iterator(chunk_size=1000))

        with open(output, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=delimiter)
            writer.writerow(headers)

            for r in qs:
                # Asegura strings ISO locales y precio como string
                ini = localtime(r.fecha_hora_inicio).isoformat(sep=" ")
                fin = localtime(r.fecha_hora_fin).isoformat(sep=" ")
                precio = str(r.precio_total) if isinstance(r.precio_total, Decimal) else r.precio_total
                writer.writerow([ini, fin, precio, r.estado])

        self.stdout.write(self.style.SUCCESS(f"✅ Exportación completada: {output}"))
