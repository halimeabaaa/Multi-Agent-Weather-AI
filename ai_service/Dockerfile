# ai_service/Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Önce bağımlılıkları yükleyerek Docker cache'ini optimize ediyoruz
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# FastAPI projesinin tüm kodlarını içeri alıyoruz
COPY . /app/