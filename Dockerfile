FROM python:3.12-slim

# Install only what's needed
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything else
COPY . .

# Run as non-root user
RUN useradd -m -u 1000 flaskuser && chown -R flaskuser:flaskuser /app
USER flaskuser

EXPOSE 5001

# Simple command - no wait script
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "4", "app:app"]