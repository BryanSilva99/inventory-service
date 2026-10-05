FROM python:3.14.7-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    INVENTORY_DB_PATH=/data/inventory.db
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY domain ./domain
COPY application ./application
COPY infrastructure ./infrastructure
COPY api ./api
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
