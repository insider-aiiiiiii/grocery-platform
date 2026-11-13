FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend/ /app/

EXPOSE 8000

# gunicorn keeps worker threads (and their database connections) alive between requests.
# Django's threaded runserver opens a new connection per request, which is very slow
# against a remote database. Tune with GUNICORN_WORKERS / GUNICORN_THREADS.
CMD ["sh", "-c", "exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-2} --threads ${GUNICORN_THREADS:-4} --timeout 60"]
