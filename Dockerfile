FROM python:3.11-slim

WORKDIR /app

# libsndfile for soundfile, ffmpeg so audioread can decode mp3s
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

COPY . .

ENV PORT=8080
ENV UPLOAD_FOLDER=/tmp
EXPOSE 8080

# Single worker with threads: librosa analysis is memory-heavy, and a long
# timeout gives numba time to JIT-compile on the first request.
CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 300 app:app
