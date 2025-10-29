import pandas as pd
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils.timezone import localtime
from core.models import Reserva
from google.cloud import bigquery

class Command(BaseCommand):
    help = "Exporta la tabla Reserva directamente a BigQuery desde Django."

    def add_arguments(self, parser):
        parser.add_argument("--project", required=True, help="ID del proyecto GCP, ej: matchplay-bi")
        parser.add_argument("--dataset", required=True, help="Dataset destino en BigQuery, ej: matchplay_data")
        parser.add_argument("--table", default="reservas", help="Nombre de la tabla destino (default: reservas)")
        parser.add_argument("--truncate", action="store_true", help="Sobrescribe la tabla en BigQuery (WRITE_TRUNCATE)")

    def handle(self, *args, **opts):
        project = opts["project"]
        dataset = opts["dataset"]
        table = opts["table"]
        truncate = opts["truncate"]

        self.stdout.write(f"🔄 Exportando reservas → BigQuery ({project}.{dataset}.{table})...")

        # Obtener los datos desde el modelo
        qs = Reserva.objects.only("fecha_hora_inicio", "fecha_hora_fin", "precio_total", "estado")
        if not qs.exists():
            self.stdout.write(self.style.WARNING("⚠️ No hay registros de Reserva para exportar."))
            return

        data = []
        for r in qs.iterator(chunk_size=1000):
            data.append({
                "fecha_hora_inicio": localtime(r.fecha_hora_inicio).isoformat(sep=" "),
                "fecha_hora_fin": localtime(r.fecha_hora_fin).isoformat(sep=" "),
                "precio_total": str(r.precio_total) if isinstance(r.precio_total, Decimal) else r.precio_total,
                "estado": r.estado,
            })

        df = pd.DataFrame(data)

        # Cliente BigQuery
        client = bigquery.Client(project=project)
        table_id = f"{project}.{dataset}.{table}"

        job_config = bigquery.LoadJobConfig(
            write_disposition=(
                bigquery.WriteDisposition.WRITE_TRUNCATE
                if truncate else bigquery.WriteDisposition.WRITE_APPEND
            ),
        )

        # Subida de datos
        job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
        job.result()

        table_obj = client.get_table(table_id)
        self.stdout.write(self.style.SUCCESS(f"✅ Carga completada: {table_obj.num_rows} filas en {table_id}"))
