FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Directori on es guarden les imatges de deteccions pujades des de l'Edge
RUN mkdir -p uploads/detections

EXPOSE 8000

# Primer apliquem les migracions pendents (ràpid si no n'hi ha cap de
# nova) i només si acaben bé arrenquem el servidor.
CMD python run_migrations.py && uvicorn main:app --host 0.0.0.0 --port 8000
