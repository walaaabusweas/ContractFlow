FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential && rm -rf /var/lib/apt/lists/*

# نسخ ملف الاعتماديات الخاص بالفرونت إند فقط
COPY pyproject.toml ./
RUN pip install --upgrade pip && \
    pip install .

# نسخ باقي ملفات مجلد الفرونت إند
COPY . .

# Hugging Face و Gradio يعتمدان على المنفذ 7860
EXPOSE 7860

CMD ["python", "app.py"]