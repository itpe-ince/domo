FROM python:3.12-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY pyproject.toml /app/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir \
        "fastapi[standard]>=0.115" \
        "uvicorn[standard]>=0.32" \
        "sqlalchemy[asyncio]>=2.0" \
        "asyncpg>=0.30" \
        "alembic>=1.14" \
        "pydantic>=2.10" \
        "pydantic-settings>=2.7" \
        "python-jose[cryptography]>=3.3" \
        "bcrypt>=4.2" \
        "python-multipart>=0.0.20" \
        "httpx>=0.28" \
        "redis>=5.2" \
        "google-auth>=2.36" \
        "requests>=2.32" \
        "Pillow>=11.0" \
        "aioboto3>=13.2" \
        "stripe>=11.3" \
        "reportlab>=4.2" \
        "pyotp>=2.9" \
        "webauthn>=2.5"

COPY . /app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
