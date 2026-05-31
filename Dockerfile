FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# تحديث وتثبيت الأدوات الأساسية فقط
RUN pip install --upgrade pip setuptools wheel

COPY pyproject.toml ./
# تثبيت المكتبات
RUN pip install .

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]