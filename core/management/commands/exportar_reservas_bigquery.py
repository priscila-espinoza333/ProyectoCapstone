import os
import psycopg2
from dotenv import load_dotenv
from google.cloud import bigquery
from django.core.management.base import BaseCommand
from datetime import datetime

class Command(BaseCommand):
    help = "Exporta datos de core_reserva desde PostgreSQL a BigQuery (reservas_raw) usando LOAD + WRITE_TRUNCATE"

    def handle(self, *args, **options):
        load_dotenv()

        # --- Conexión a PostgreSQL ---
        pg_conn = psycopg2.connect(
            host=os.getenv("PG_HOST"),
            port=os.getenv("PG_PORT"),
            dbname=os.getenv("PG_DB"),
            user=os.getenv("PG_USER"),
            password=os.getenv("PG_PASSWORD"),
        )
        pg_cursor = pg_conn.cursor()
        tabla_reserva = os.getenv("PG_RESERVA_TABLE", "core_reserva")

        self.stdout.write(self.style.NOTICE(f"Leyendo datos desde PostgreSQL: tabla {tabla_reserva}"))

        pg_cursor.execute(f"""
            SELECT
                id,
                estado,
                creado_en,
                cancha_id,
                usuario_id,
                actualizado_en,
                email_contacto,
                fecha_hora_fin,
                fecha_hora_inicio,
                nombre_contacto,
                precio_total,
                telefono_contacto
            FROM {tabla_reserva};
        """)
        rows = pg_cursor.fetchall()

        # Preparar filas para BigQuery
        

        def to_iso(dt):
            if dt is None:
                return None
            if isinstance(dt, datetime):
                return dt.isoformat()
            return dt

        bq_rows = [
            {
                "id": r[0],
                "estado": r[1],
                "creado_en": to_iso(r[2]),
                "cancha_id": r[3],
                "usuario_id": r[4],
                "actualizado_en": to_iso(r[5]),
                "email_contacto": r[6],
                "fecha_hora_fin": to_iso(r[7]),
                "fecha_hora_inicio": to_iso(r[8]),
                "nombre_contacto": r[9],
                "precio_total": float(r[10]) if r[10] is not None else 0.0,
                "telefono_contacto": r[11],
            }
            for r in rows
        ]


        # --- Configuración BigQuery ---
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        project_id = os.getenv("GCP_PROJECT_ID")
        dataset_id = os.getenv("GCP_BQ_DATASET")
        table_name = os.getenv("GCP_BQ_TABLE")
        table_id = f"{project_id}.{dataset_id}.{table_name}"

        client = bigquery.Client(project=project_id)

        schema = [
            bigquery.SchemaField("id", "INT64", mode="REQUIRED"),
            bigquery.SchemaField("estado", "STRING"),
            bigquery.SchemaField("creado_en", "TIMESTAMP"),
            bigquery.SchemaField("cancha_id", "INT64"),
            bigquery.SchemaField("usuario_id", "INT64"),
            bigquery.SchemaField("actualizado_en", "TIMESTAMP"),
            bigquery.SchemaField("email_contacto", "STRING"),
            bigquery.SchemaField("fecha_hora_fin", "TIMESTAMP"),
            bigquery.SchemaField("fecha_hora_inicio", "TIMESTAMP"),
            bigquery.SchemaField("nombre_contacto", "STRING"),
            bigquery.SchemaField("precio_total", "NUMERIC"),
            bigquery.SchemaField("telefono_contacto", "STRING"),
        ]

        # Crear tabla si no existe
        try:
            client.get_table(table_id)
            self.stdout.write(self.style.SUCCESS(f"La tabla {table_id} ya existe."))
        except Exception:
            table = bigquery.Table(table_id, schema=schema)
            client.create_table(table)
            self.stdout.write(self.style.SUCCESS(f"Tabla creada en BigQuery: {table_id}"))

        # Cargar datos con LOAD JOB + WRITE_TRUNCATE (sin DELETE, sin INSERT DML)
        self.stdout.write(self.style.NOTICE(
            f"Cargando {len(bq_rows)} filas en {table_id} con WRITE_TRUNCATE..."
        ))

        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        )

        load_job = client.load_table_from_json(
            bq_rows,
            table_id,
            job_config=job_config,
        )

        load_job.result()  # Esperar a que termine

        self.stdout.write(self.style.SUCCESS(
            f"Carga completada. Filas cargadas: {len(bq_rows)}"
        ))

        pg_cursor.close()
        pg_conn.close()
