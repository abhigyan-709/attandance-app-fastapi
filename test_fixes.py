#!/usr/bin/env python3
"""
Test script to verify bcrypt and news creation fixes
"""

def test_bcrypt_import():
    """Test bcrypt import and passlib compatibility"""
    try:
        import bcrypt
        print(f"✅ bcrypt version: {bcrypt.__version__}")
        
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
        
        # Test password hashing
        test_password = "test123"
        hashed = pwd_context.hash(test_password)
        verified = pwd_context.verify(test_password, hashed)
        
        print("✅ passlib bcrypt integration works!")
        print(f"✅ Password hashing test: {'PASSED' if verified else 'FAILED'}")
        return True
        
    except Exception as e:
        print(f"❌ bcrypt/passlib test failed: {e}")
        return False

def test_news_model():
    """Test news model without language field"""
    try:
        from models.news import NewsPost
        from datetime import datetime
        
        # Test creating a news post without language field
        news = NewsPost(
            title="Test News",
            content="Test content",
            author_username="test_user",
            categories="test"
        )
        
        # Check that language field is not in the model dict
        news_dict = news.model_dump()
        if "language" in news_dict:
            print("❌ Language field still present in news model")
            return False
        
        print("✅ NewsPost model created successfully without language field")
        print(f"✅ News fields: {list(news_dict.keys())}")
        return True
        
    except Exception as e:
        print(f"❌ News model test failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing fixes for bcrypt compatibility and MongoDB language error...\n")
    
    bcrypt_ok = test_bcrypt_import()
    news_ok = test_news_model()
    
    print(f"\n{'='*50}")
    print(f"Overall Status: {'✅ ALL TESTS PASSED' if (bcrypt_ok and news_ok) else '❌ SOME TESTS FAILED'}")
    print(f"{'='*50}")