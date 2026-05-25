FROM python:3.12-slim

WORKDIR /app

COPY services/ordenes_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/ordenes_service/ .
COPY services/_shared/ /app/_shared/

RUN mkdir -p /app/data /app/uploads/evidencias

EXPOSE 5001

CMD ["python", "app.py"]
