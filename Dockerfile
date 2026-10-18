FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid 10001 poker \
    && useradd --uid 10001 --gid poker --no-create-home poker
COPY backend/ /app/backend/
COPY deploy/smoke_test.py /app/deploy/smoke_test.py
COPY config/game_config.json config/agent_personas.json /app/config/
RUN mkdir -p /app/data /app/logs && chown -R poker:poker /app
USER poker
WORKDIR /app/backend
EXPOSE 8000
# Sessions live in memory: run exactly one worker.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]
