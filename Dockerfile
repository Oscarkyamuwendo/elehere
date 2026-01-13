FROM python:3.12-slim

# Install only what's needed
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt gunicorn authlib PyJWT cryptography requests

# Copy everything else
COPY . .

# Create uploads directory
RUN mkdir -p static/uploads && chmod -R 755 static/uploads

# Run as non-root user
RUN useradd -m -u 1000 flaskuser && chown -R flaskuser:flaskuser /app
USER flaskuser

# Railway uses PORT environment variable
ENV PORT=5001
EXPOSE 5001

# Health check for Railway - FIXED: Use hardcoded port in health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5001/health || exit 1

# Simple command - Railway will override PORT if needed
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "4", "app:app"]