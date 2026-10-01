# Servicio del agente (sustituye a Agent Runtime). Contexto de build: la raiz.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:/app/comun
WORKDIR /app
COPY agente/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY agente/ ./
COPY comun/ ./comun/
COPY pruebas/ ./pruebas/
RUN useradd -u 1000 -m app && chown -R app /app
USER app
EXPOSE 8000
CMD ["uvicorn", "servidor:app", "--host", "0.0.0.0", "--port", "8000"]
