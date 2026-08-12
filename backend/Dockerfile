FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml requirements.txt ./
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
COPY docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .
RUN addgroup --system ctec && adduser --system --ingroup ctec ctec
USER ctec
EXPOSE 8000
ENTRYPOINT ["./docker-entrypoint.sh"]

