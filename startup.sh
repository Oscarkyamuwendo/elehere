#!/bin/bash
# startup.sh

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Install dependencies
pip install -r requirements.txt

# Set up database
python -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database tables created')
"

# Run the app
echo "Starting Flask app on port 5000..."
echo "Open: https://${CODESPACE_NAME}-5000.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}"
gunicorn -w 4 -b 0.0.0.0:5000 --reload app:app