FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY stubs/ stubs/
COPY scripts/seed.py scripts/seed.py
COPY alembic.ini .
COPY migrations/ migrations/

ENV FLASK_APP=app
ENV AUTH_MODE=stub
ENV CMDB_MODE=stub
ENV CMDB_STUB_DATA_PATH=./stubs/cmdb/

EXPOSE 5000

CMD ["sh", "-c", "alembic upgrade head && python scripts/seed.py && flask run --host=0.0.0.0 --port=5000"]
