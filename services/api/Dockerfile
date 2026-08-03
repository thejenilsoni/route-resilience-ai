FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/ml:/app

WORKDIR /app
COPY pyproject.toml ./
COPY ml ./ml
COPY services ./services
RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["uvicorn", "services.api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
