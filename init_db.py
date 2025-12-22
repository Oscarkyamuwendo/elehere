#!/usr/bin/env python3
"""
Database initialization script for Elehere app.
"""
import os
import sys
from sqlalchemy import text

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import app, db
    
    with app.app_context():
        print("🗄️  Initializing database...")
        
        # Test connection first (SQLAlchemy 2.0 requires text() wrapper)
        try:
            db.session.execute(text('SELECT 1'))
            print("✅ Database connection successful")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            print("\n💡 Make sure:")
            print("1. MySQL container is running: docker-compose up -d db")
            print("2. Database 'elehere_db' exists")
            print("3. User 'user' has permissions")
            sys.exit(1)
        
        # Create tables
        print("📝 Creating tables...")
        db.create_all()
        print("✅ Tables created successfully")
        
        # Show created tables
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        if tables:
            print(f"📊 Tables in database ({len(tables)}):")
            for table in tables:
                print(f"  - {table}")
        else:
            print("⚠ No tables found - check your models")
            
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\n💡 Install dependencies: pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)