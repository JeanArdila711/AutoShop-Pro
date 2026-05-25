FROM python:3.12-slim

WORKDIR /app

COPY services/facturacion_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/facturacion_service/ .
COPY services/_shared/ /app/_shared/

EXPOSE 5003

CMD ["python", "app.py"]
