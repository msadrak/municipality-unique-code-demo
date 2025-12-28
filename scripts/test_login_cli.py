"""
Test Login CLI - Verifies password hashing works correctly.

This script:
1. Fetches test_user from the database
2. Runs verify_password() manually
3. Prints the result (True/False)

Usage:
    python scripts/test_login_cli.py
"""

import sys
sys.path.insert(0, '.')

from app.database import SessionLocal
from app.models import User
from app.auth_utils import verify_password, is_legacy_hash

def test_login():
    print("=" * 60)
    print("LOGIN VERIFICATION TEST")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Fetch test_user
        user = db.query(User).filter(User.username == "test_user").first()
        
        if not user:
            print("❌ User 'test_user' not found in database!")
            print("   Run: python seed_users.py")
            return
        
        print(f"\n📋 User Details:")
        print(f"   Username: {user.username}")
        print(f"   Full Name: {user.full_name}")
        print(f"   Role: {user.role}")
        print(f"   Active: {user.is_active}")
        print(f"   Zone ID: {user.default_zone_id}")
        print(f"   Section ID: {user.default_section_id}")
        
        # Analyze hash type
        hash_preview = user.password_hash[:50] + "..." if len(user.password_hash) > 50 else user.password_hash
        print(f"\n🔐 Password Hash:")
        print(f"   Preview: {hash_preview}")
        print(f"   Is Legacy (SHA256): {is_legacy_hash(user.password_hash)}")
        print(f"   Is Argon2: {user.password_hash.startswith('$argon2')}")
        
        # Test verification
        print(f"\n🧪 Verification Tests:")
        
        # Test 1: Correct password
        test_password = "user123"
        result = verify_password(test_password, user.password_hash)
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   Password '{test_password}': {result} {status}")
        
        # Test 2: Wrong password
        wrong_password = "wrongpassword"
        result_wrong = verify_password(wrong_password, user.password_hash)
        status_wrong = "✅ PASS (correctly rejected)" if not result_wrong else "❌ FAIL (should reject)"
        print(f"   Password '{wrong_password}': {result_wrong} {status_wrong}")
        
        # Summary
        print("\n" + "=" * 60)
        if result and not result_wrong:
            print("✅ All verification tests passed!")
            print("   Login with test_user / user123 should work.")
        else:
            print("❌ Verification tests failed!")
            print("   Run: python seed_users.py to fix password hashes.")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    test_login()
