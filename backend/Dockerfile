# backend/Dockerfile
FROM python:3.11-slim

# Python'un çıktıları (print loglarını) anlık olarak Docker terminaline basması için
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# MySQL istemcisi (mysqlclient) derlenirken Linux tarafında gereken paketleri kuruyoruz
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Konteyner içindeki çalışma dizini
WORKDIR /app

# Docker Cache mekanizmasından yararlanmak için önce bağımlılıkları kopyalayıp kuruyoruz
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Projenin kalan tüm kodlarını konteyner içine kopyalıyoruz
COPY . /app/