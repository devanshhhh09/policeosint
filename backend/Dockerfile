FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y \
    gcc libpq-dev curl exiftool \
    libpango-1.0-0 libpangoft2-1.0-0 libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 libffi-dev libcairo2 \
    gir1.2-pango-1.0 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout=120 --retries=5 -r requirements.txt
COPY . .
EXPOSE 8000
