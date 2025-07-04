# Use official Python base image (slim is lighter)
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=stock_prediction_main.settings
ENV DEBUG=False
ENV MODEL_PATH=stock_prediction_model.keras
ENV ALLOWED_HOSTS=*

# Set work directory
WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    build-essential libpq-dev \
    libjpeg-dev zlib1g-dev libpng-dev libfreetype6-dev \
    libssl-dev libffi-dev curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the full project into the container
COPY . .

# Collect static files
RUN mkdir -p /app/staticfiles /app/media
RUN python manage.py collectstatic --noinput

# Expose port (optional if docker-compose is handling it)
EXPOSE 8000

# Start Gunicorn
CMD ["gunicorn", "stock_prediction_main.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
