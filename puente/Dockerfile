# Puente y consola (puntos 1 y 4). Contexto de build: la raiz.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY puente/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY puente/main.py puente/consola.html ./
# El mismo cliente de Guardrails que usa el agente: una sola copia en el repo.
COPY agente/bank_agents/shared/guardrails.py ./guardrails.py
COPY comun/agente_cliente.py ./
RUN useradd -u 1000 -m app && chown -R app /app
USER app
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
