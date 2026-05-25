# Dockerfile  (para el monolito Django)
FROM python:3.12-slim

WORKDIR /app

# gettext — necesario para compilar archivos .po → .mo (i18n)
RUN apt-get update && apt-get install -y gettext && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias primero (aprovecha el cache de Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente
COPY . .

# Compilar traducciones .po → .mo
RUN python manage.py compilemessages

# Puerto interno de Django
EXPOSE 8000

# Comando de arranque (sin reloader en producción)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
