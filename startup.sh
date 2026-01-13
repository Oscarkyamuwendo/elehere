#!/bin/bash
# start.sh - For local development

echo "Starting Elehere EHR System..."
echo "Environment: ${FLASK_ENV:-development}"

# Create necessary directories
mkdir -p static/uploads
mkdir -p logs

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Set environment variables for local development
export FLASK_ENV=development
export APP_URL=http://localhost:5000
export DATABASE_URL=mysql+pymysql://root:password@localhost:3307/elehere

# Run the application
echo "Starting Flask on http://localhost:5000"
python app.py