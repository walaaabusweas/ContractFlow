FROM public.ecr.aws/lambda/python:3.12

WORKDIR /var/task

# 1. تثبيت uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 2. نسخ ملفات الإعدادات
COPY pyproject.toml ./
RUN touch README.md

# 3. [Layer 1 ~150MB] تثبيت أدوات البناء و PyTorch CPU
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system hatchling setuptools && \
    uv pip install --system torch --index-url https://download.pytorch.org/whl/cpu

# 4. [Layer 2 ~500MB] تثبيت مكتبات الـ Transformers والـ AI بشكل مستقل
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system sentence-transformers transformers langchain-core

# 5. [Layer 3 ~1GB] تنزيل الأوزان الأساسية للنموذج (Base Weights)
RUN mkdir -p /opt/ml/models && \
    python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='BAAI/bge-m3', local_dir='/opt/ml/models/bge-m3', allow_patterns=['*.json', '*.txt', '*.model'])"

# 6. [Layer 4 ~1.2GB] تنزيل ملفات الـ Safetensors/Bin الكبيرة للنموذج
RUN python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='BAAI/bge-m3', local_dir='/opt/ml/models/bge-m3', allow_patterns=['*.safetensors', '*.bin'])"

# 7. [Layer 5 ~200MB] تثبيت باقي اعتمادات المشروع
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system --no-build-isolation .

# 8. [Layer 6 ~ميجابايت قليل] نسخ كود التطبيق
COPY . .

CMD [ "main.handler" ]