#!/usr/bin/env python3
import subprocess
import time
import sys
import os

def start_mysql():
    """Start MySQL service if not running"""
    try:
        # Check if MySQL is running
        result = subprocess.run(['brew', 'services', 'list'], 
                              capture_output=True, text=True)
        if 'mysql' not in result.stdout or 'started' not in result.stdout:
            print("Starting MySQL...")
            subprocess.run(['brew', 'services', 'start', 'mysql'])
            time.sleep(3)  # Wait for MySQL to start
    except Exception as e:
        print(f"Note: MySQL might need to be started manually: {e}")

def create_database():
    """Create database if it doesn't exist"""
    try:
        subprocess.run([
            'mysql', '-u', 'root', '-e',
            'CREATE DATABASE IF NOT EXISTS elehere_db;'
        ], check=False)
    except Exception as e:
        print(f"Note: Could not create database (might already exist): {e}")

def start_app():
    """Start the Flask app with Gunicorn"""
    print("Starting Flask app with Gunicorn...")
    os.system(f'{sys.executable} -m gunicorn -w 4 -b 0.0.0.0:5000 --reload app:app')

if __name__ == "__main__":
    print("Starting Elehere application...")
    start_mysql()
    create_database()
    start_app()