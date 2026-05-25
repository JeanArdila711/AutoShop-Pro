FROM python:3.12-slim

WORKDIR /app

COPY services/citas_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/citas_service/ .
COPY services/_shared/ /app/_shared/

RUN mkdir -p /app/data

EXPOSE 5004

CMD ["python", "app.py"]
