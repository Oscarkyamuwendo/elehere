#!/bin/bash

# Activate virtual environment
source /Volumes/COLLECTION/PROJECT/elehere/venv/bin/activate

# Ensure MySQL is running
brew services start mysql 2>/dev/null || true

# Wait for MySQL to be ready
sleep 2

# Check if database exists, create if not
mysql -u root -e "CREATE DATABASE IF NOT EXISTS elehere_db;" 2>/dev/null || echo "MySQL might not be running"

# Run the app with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 --reload app:app