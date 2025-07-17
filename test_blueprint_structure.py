"""
Test script to verify that the new blueprint-based application structure works.
This tests the app_new.py structure we created.
"""
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_blueprint_imports():
    """Test that all blueprints can be imported without errors."""
    try:
        from blueprints.main import main_bp
        from blueprints.api import api_bp
        from blueprints.round2 import round2_bp
        print("✅ All blueprints imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Blueprint import failed: {e}")
        return False

def test_services_imports():
    """Test that services can be imported without errors."""
    try:
        from services import (
            VideoInteractionService, 
            VideoSelectionService, 
            ParticipantService, 
            AdditionalInfoService, 
            StrategyRedirectService
        )
        print("✅ All services imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Service import failed: {e}")
        return False

def test_app_new_structure():
    """Test that the new app structure can be loaded."""
    try:
        # This would fail if there are any import issues
        import app_new
        print("✅ app_new.py structure loads successfully")
        return True
    except Exception as e:
        print(f"❌ app_new.py failed to load: {e}")
        return False

if __name__ == "__main__":
    print("Testing Blueprint Structure...")
    print("=" * 50)
    
    all_tests_passed = True
    
    all_tests_passed &= test_blueprint_imports()
    all_tests_passed &= test_services_imports() 
    all_tests_passed &= test_app_new_structure()
    
    print("=" * 50)
    if all_tests_passed:
        print("🎉 All blueprint structure tests passed!")
        print("✅ Ready to migrate to the new structure")
    else:
        print("❌ Some tests failed. Check the import issues above.")
    
    print("=" * 50)
