🏥 Elehere - Medical Records Management System
https://railway.app/button.svg
https://img.shields.io/badge/Docker-%E2%9C%93-blue
https://img.shields.io/badge/MySQL-8.0-orange
https://img.shields.io/badge/Flask-3.0.0-green

A complete Flask web application for managing patient medical records with Docker containerization, automated CI/CD pipeline, and production deployment.


✨ Features
Patient Management: Add, edit, and view patient records

Doctor Authentication: Secure login and session management

File Upload: Radiology image storage and management

Dockerized: Full container support for easy deployment

CI/CD Pipeline: Automated testing and deployment via GitHub Actions

Production Ready: Gunicorn WSGI server, health checks, security

Database: MySQL 8.0 with automatic initialization

🚀 Quick Start
Prerequisites
Docker Desktop (Download)

Git (Download)

Get Started in 60 Seconds
bash
# Clone and run
git clone https://github.com/YOUR_USERNAME/elehere.git
cd elehere
docker-compose up --build

# Open in browser: http://localhost:5000
# Check health: http://localhost:5000/health
🐳 Docker Commands Cheat Sheet
Command	Description
docker-compose up --build	Build and start all services
docker-compose down -v	Stop and remove everything
docker-compose logs -f web	View application logs
docker-compose ps	Check container status
docker-compose exec db mysql -u user -p	Access MySQL shell
docker-compose build --no-cache	Force rebuild images
📦 Project Structure
text
elehere/
├── app.py                    # Main Flask application
├── Dockerfile               # Production container setup
├── docker-compose.yml       # Development environment
├── requirements.txt         # Python dependencies
├── wait-for-db.sh          # Database readiness script
├── .github/workflows/      # CI/CD pipeline
│   └── ci-cd.yml          # GitHub Actions workflow
├── railway.json            # Railway deployment config
├── static/                 # CSS, JavaScript, images
├── templates/              # HTML templates
│   ├── base.html          # Base template
│   ├── add_patient.html   # Add patient form
│   ├── edit_patient.html  # Edit patient form
│   └── view_patients.html # Patient listing
├── uploads/                # File uploads directory
└── README.md              # This file


🔧 Core Files Explained
Dockerfile
dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y gcc default-libmysqlclient-dev pkg-config curl netcat-openbsd
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt gunicorn
COPY wait-for-db.sh /wait-for-db.sh
RUN chmod +x /wait-for-db.sh
COPY . .
RUN useradd -m -u 1000 flaskuser && chown -R flaskuser:flaskuser /app
USER flaskuser
EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1
CMD ["/wait-for-db.sh", "db", "3306", "gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "app:app"]
docker-compose.yml
yaml
services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=development
      - DATABASE_URL=mysql+pymysql://user:password@db:3306/elehere_db
      - SECRET_KEY=dev-secret-key-change-in-production
    depends_on:
      - db
    volumes:
      - ./uploads:/app/uploads

  db:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: rootpassword
      MYSQL_DATABASE: elehere_db
      MYSQL_USER: user
      MYSQL_PASSWORD: password
    ports:
      - "3307:3306"
    volumes:
      - mysql_data:/var/lib/mysql

volumes:
  mysql_data:
wait-for-db.sh
bash
#!/bin/bash
set -e
host="$1"
port="$2"
shift 2
cmd="$@"
until nc -z "$host" "$port"; do
  >&2 echo "MySQL is unavailable - sleeping"
  sleep 2
done
>&2 echo "MySQL is up - executing command"
exec $cmd
🗄️ Database Configuration
Automatic Setup (Docker)
The database is automatically configured with:

Database: elehere_db

User: user / password

Root: root / rootpassword

Port: 3306 (container), 3307 (host)

Manual Setup
bash
# Start MySQL service
brew services start mysql  # macOS
# or: sudo systemctl start mysql  # Linux

# Create database
mysql -u root -p << EOF
CREATE DATABASE elehere_db;
CREATE USER 'elehere_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON elehere_db.* TO 'elehere_user'@'localhost';
FLUSH PRIVILEGES;
EOF
🔄 CI/CD Pipeline
Automated Workflow
Push to GitHub → Triggers GitHub Actions

Run Tests → MySQL integration tests

If Tests Pass → Auto-deploy to Railway

Live Deployment → your-app.up.railway.app

GitHub Actions Configuration
yaml
name: CI/CD Pipeline
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: root
          MYSQL_DATABASE: test_db
    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v4
      with:
        python-version: '3.12'
    - run: pip install -r requirements.txt
    - run: python -c "from app import app; print('✅ App imports')"
    
  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: railway/action@v1.0.4
      with:
        token: ${{ secrets.RAILWAY_TOKEN }}
🌐 Environment Setup
.env.example
env
# Flask Configuration
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=mysql+pymysql://user:password@db:3306/elehere_db

# Email (Optional)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# File Uploads
UPLOAD_FOLDER=./uploads
MAX_CONTENT_LENGTH=16777216  # 16MB
🐛 Troubleshooting Guide
Common Issues & Solutions
Problem	Solution
Port 5000 in use (macOS)	Use port 5001: docker-compose.yml: "5001:5000"
MySQL connection refused	Wait for DB init: sleep 10 after docker-compose up -d db
"ModuleNotFoundError: flask"	Rebuild: docker-compose build --no-cache
SQL syntax error	Fix: allergies=', '.join(request.form.getlist('allergies'))
Docker not starting	Open Docker Desktop app first
Quick Diagnostics
bash
# Check if Docker is running
docker ps

# Test database connection
docker-compose exec db mysql -u user -ppassword -e "SELECT 1;"

# View application logs
docker-compose logs --tail=20 web

# Check health endpoint
curl -s http://localhost:5000/health | jq

# Test from inside container
docker-compose exec web python -c "
from app import app
with app.test_client() as client:
    resp = client.get('/health')
    print(f'Status: {resp.status_code}')
"


Railway (Recommended - Free Tier)
Sign up at railway.app with GitHub

Create project and connect repository

Add MySQL database service

Set environment variables:

DATABASE_URL (Railway provides)

SECRET_KEY (generate secure key)

FLASK_ENV=production

Push to GitHub → Auto-deploy

Railway CLI
bash
# Install CLI
npm i -g @railway/cli

# Deploy
railway login
railway link
railway up
Manual Production
bash
# Build production image
docker build -t elehere:prod .

# Run with environment variables
docker run -d -p 5000:5000 \
  -e FLASK_ENV=production \
  -e SECRET_KEY=your-secret \
  -e DATABASE_URL=your-db-url \
  -v elehere-uploads:/app/uploads \
  elehere:prod
📦 Dependencies
Key Packages
Flask 3.0.0 - Web framework

Flask-SQLAlchemy 3.1.1 - Database ORM

Flask-Bcrypt 1.0.1 - Password hashing

MySQL 8.0 - Database server

Gunicorn 21.2.0 - Production WSGI server

cryptography 46.0.3 - MySQL 8 auth support

Complete List
txt
Flask==3.0.0
Werkzeug==3.0.1
Jinja2==3.1.3
Flask-SQLAlchemy==3.1.1
Flask-Bcrypt==1.0.1
Flask-Mail==0.9.1
Flask-Migrate==4.0.5
SQLAlchemy==2.0.23
pymysql==1.1.0
cryptography>=42.0.0
gunicorn==21.2.0
python-dotenv==1.0.0
🤝 Contributing
Fork the repository

Create feature branch: git checkout -b feature/amazing-feature

Commit changes: git commit -m 'Add amazing feature'

Push to branch: git push origin feature/amazing-feature

Open Pull Request

Development Guidelines
Follow PEP 8 style guide

Write descriptive commit messages

Update documentation as needed

Test changes before submitting

📄 License
MIT License - see LICENSE file for details.

📞 Support
GitHub Issues: Report bugs

Email: your-email@example.com

🎯 Quick Reference
Application URLs
Local Development: http://localhost:5000

Health Check: http://localhost:5000/health

MySQL Admin: localhost:3307 (user: user, pass: password)

Default Credentials (Development)
Database: elehere_db

User: user / password

Root: root / rootpassword

Important Notes
Uses Python 3.12 (required for SQLAlchemy compatibility)

MySQL 8.0 with caching_sha2_password authentication

File uploads stored in ./uploads directory

Auto-deployment on push to main branch

HTTPS/SSL automatically provided by Railway

Last Updated: December 2024 | Version: 1.0.0

🚀 Final Deployment Checklist
Replace YOUR_USERNAME in GitHub URLs

Update email in support section

Set strong SECRET_KEY in production

Configure email credentials (optional)

Test full workflow: git push origin main

Verify auto-deployment to Railway

Ready to deploy? Run: git add . && git commit -m "Ready for deployment" && git push origin main