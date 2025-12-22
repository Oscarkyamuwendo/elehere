FROM python:3.12-slim

WORKDIR /app

# Install dependencies (netcat-openbsd is needed for the wait script)
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the wait script first
COPY wait-for-db.sh /wait-for-db.sh
# Make the script executable inside the container[citation:4]
RUN chmod +x /wait-for-db.sh

# Copy app
COPY . .

# Expose port
EXPOSE 5000

# Use the wait script to start your app
CMD ["/wait-for-db.sh", "db", "3306", "python", "app.py"]