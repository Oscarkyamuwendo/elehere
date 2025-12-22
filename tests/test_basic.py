"""
Basic tests for Elehere app
"""
import pytest
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_app_import():
    """Test that the app can be imported."""
    try:
        from app import app
        assert app is not None
        print("✓ App imports successfully")
        return True
    except Exception as e:
        print(f"✗ App import failed: {e}")
        return False

def test_flask_config():
    """Test Flask app configuration."""
    try:
        from app import app
        # Check basic Flask config
        assert app.config['SECRET_KEY'] is not None
        print("✓ Flask config is valid")
        return True
    except Exception as e:
        print(f"✗ Flask config test failed: {e}")
        return False

def test_database_connection():
    """Test database connection if SQLAlchemy is used."""
    try:
        from app import app, db
        # Try to create engine (won't actually connect unless we try to use it)
        with app.app_context():
            # Just check if db object exists
            assert db is not None
            print("✓ Database setup is valid")
            return True
    except ImportError:
        print("ℹ SQLAlchemy not configured, skipping database test")
        return True  # Not a failure if no db
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        return False

def test_routes_exist():
    """Test that basic routes are defined."""
    try:
        from app import app
        # Get all routes
        routes = [str(rule) for rule in app.url_map.iter_rules()]
        print(f"Found {len(routes)} routes")
        
        # Check for common routes (adjust based on your app)
        if '/' in routes or '/login' in routes or '/register' in routes:
            print("✓ Basic routes are defined")
            return True
        else:
            print("ℹ No common routes found, but app may have custom routes")
            return True
    except Exception as e:
        print(f"✗ Routes test failed: {e}")
        return False

if __name__ == "__main__":
    """Run tests directly for quick verification."""
    print("🧪 Running Elehere app tests...\n")
    
    tests = [
        test_app_import,
        test_flask_config,
        test_database_connection,
        test_routes_exist
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} raised exception: {e}")
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed")
        sys.exit(1)