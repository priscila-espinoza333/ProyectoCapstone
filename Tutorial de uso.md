
# Documentación de la API

## Introducción

Este documento es un paso a paso para levantar el entorno virutal, crear las tablas localmente, describe los endpoints disponibles en la API, los parámetros necesarios para cada uno, los verbos HTTP utilizados y ejemplos de las respuestas esperadas.

## Requisitos

Antes de comenzar, asegúrate de tener instalados los siguientes requisitos:

- Python

## Instalación

1. Crea un entorno virtual:
   ```bash
   python -m venv venv
   ```


2. Activa el entorno virtual:

   - En Windows:
     ```bash
     .\venv311\Scripts\activate
     ```
   - En macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

3. Instala las dependencias:

   ```bash
   pip install -r requirements.txt


   ```

4. Aplica las migraciones:

   ```bash
   cd core
   python manage.py makemigrations core
   python manage.py migrate
   ```

5. Ejecuta el servidor de desarrollo:
   ```bash
   
  python manage.py runserver
   ```



### Resumen de Endpoints

| Endpoint                                      | Método HTTP | Descripción                 |
| --------------------------------------------- | ----------- | --------------------------- |
| `/api/productos/`                             | `GET`       | Listar productos            |
| `/api/productos/`                             | `POST`      | Crear producto              |
| `/api/productos/<str:codigo>/`                | `GET`       | Detalle de producto         |
| `/api/productos/<str:codigo>/`                | `PUT`       | Actualizar producto         |
| `/api/productos/<str:codigo>/`                | `DELETE`    | Eliminar producto           |
| `/api/carro/productos/`                       | `POST`      | Agregar producto al carro   |
| `/api/carro/detalle/`                         | `GET`       | Obtener detalle del carro   |
| `/api/carro/productos/<int:producto_codigo>/` | `DELETE`    | Eliminar producto del carro |
| `/api/carro/finalizar/`                       | `POST`      | Pagar y finalizar el carro  |

## Notas
-