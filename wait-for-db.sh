#!/bin/bash
set -e

# Wait for MySQL to be ready using mysqladmin
echo "Waiting for MySQL to be ready..."
for i in {1..30}; do
    if mysqladmin ping -h"db" --silent; then
        echo "MySQL is up!"
        break
    fi
    echo "Waiting for database connection... (attempt $i/30)"
    sleep 2
done

# Start gunicorn
echo "Starting gunicorn..."
exec gunicorn --bind 0.0.0.0:5001 --workers 4 --threads 4 --access-logfile - app:app