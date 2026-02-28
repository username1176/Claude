FROM python:3.12-slim

WORKDIR /app

# System deps for cyvcf2, scipy, and other C-extension packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc libhts-dev zlib1g-dev \
        gfortran libopenblas-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create data directories
RUN mkdir -p data/uploads/tmp data/uploads/enc data/db

ENV FLASK_ENV=production
EXPOSE 5000

CMD ["gunicorn", "wsgi:app", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "120"]
