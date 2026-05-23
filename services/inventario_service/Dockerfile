# Dockerfile para inventario_service (Flask + SQLite local)
FROM python:3.12-slim

WORKDIR /app

# Copiar requirements desde la carpeta del servicio
COPY services/inventario_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el código del microservicio
COPY services/inventario_service/ .

# Carpeta para SQLite persistente del microservicio
RUN mkdir -p /app/data

EXPOSE 5002

CMD ["python", "app.py"]
