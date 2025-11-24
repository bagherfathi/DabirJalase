FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PY_SERVICES_HOST=0.0.0.0 \
    PY_SERVICES_PORT=8000

WORKDIR /app

COPY python_services/requirements-lean.txt /tmp/requirements-lean.txt
RUN pip install --no-cache-dir -r /tmp/requirements-lean.txt

COPY python_services /app/python_services
COPY fastapi /app/fastapi
COPY pydantic /app/pydantic
ENV PYTHONPATH=/app

EXPOSE 8000
CMD ["python", "-m", "python_services"]
