FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=run.py
ENV FLASK_ENV=production

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq-dev curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --no-create-home appuser

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY . .

RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 5050

CMD ["python", "run.py"]