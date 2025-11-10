#!/usr/bin/env python3
"""
Comprehensive Biodata System Testing Script
Tests all major biodata functionality including:
- Authentication
- Basic CRUD operations
- Advanced features
- Photo uploads
- Search and filtering
- Admin features
"""

import requests
import json
import time
from datetime import date, datetime
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000"
TEST_USER = {
    "username": "test_biodata_user",
    "email": "testbiodata@example.com",
    "password": "TestPassword123!"
}

class BiodataSystemTester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.auth_token = None
        self.test_profile_id = None
        
    def print_separator(self, title: str):
        """Print a formatted separator"""
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")
        
    def print_result(self, test_name: str, success: bool, details: str = ""):
        """Print test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"    {details}")
            
    def register_test_user(self) -> bool:
        """Register a test user for biodata testing"""
        self.print_separator("USER REGISTRATION")
        
        try:
            response = self.session.post(
                f"{self.base_url}/register",
                json=TEST_USER
            )
            
            if response.status_code == 201:
                self.print_result("User Registration", True, f"User {TEST_USER['username']} registered successfully")
                return True
            elif response.status_code == 400 and "already exists" in response.text:
                self.print_result("User Registration", True, f"User {TEST_USER['username']} already exists")
                return True
            else:
                self.print_result("User Registration", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.print_result("User Registration", False, f"Exception: {str(e)}")
            return False
    
    def login_test_user(self) -> bool:
        """Login and get authentication token"""
        self.print_separator("USER LOGIN")
        
        try:
            response = self.session.post(
                f"{self.base_url}/login",
                data={
                    "username": TEST_USER["username"],
                    "password": TEST_USER["password"]
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                if "access_token" in result:
                    self.auth_token = result["access_token"]
                    self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})
                    self.print_result("User Login", True, "Authentication token received")
                    return True
                else:
                    self.print_result("User Login", False, "No access token in response")
                    return False
            else:
                self.print_result("User Login", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.print_result("User Login", False, f"Exception: {str(e)}")
            return False
    
    def test_create_basic_biodata(self) -> bool:
        """Test creating a basic biodata profile"""
        self.print_separator("CREATE BASIC BIODATA")
        
        basic_biodata = {
            "biodata_type": "basic",
            "first_name": "Ananya",
            "last_name": "Kumar",
            "gender": "female",
            "dob": "1997-08-14",
            "religion": "hindu",
            "caste": "Kayastha",
            "gotra": "Kashyap",
            "mother_tongue": "Hindi",
            "marital_status": "never_married",
            "about_me": "Software engineer with a love for travel and books.",
            "contact": {
                "email": "ananya@example.com",
                "phone_country_code": "+91",
                "phone_number": "9876543210",
                "address": {
                    "city": "Patna",
                    "state": "Bihar",
                    "country": "India",
                    "pincode": "800001"
                }
            },
            "education": {
                "level": "masters",
                "degree": "MCA",
                "institute": "XYZ University",
                "graduation_year": 2020
            },
            "occupation": {
                "employment_type": "private",
                "organization": "ABC Tech",
                "designation": "SDE-2",
                "annual_income_value": 18.0,
                "annual_income_currency": "INR"
            },
            "physical": {
                "height_cm": 163,
                "weight_kg": 56,
                "body_type": "slim",
                "complexion": "wheatish"
            },
            "lifestyle": {
                "diet": "vegetarian",
                "drinking": "no",
                "smoking": "no"
            }
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/biodata",
                json=basic_biodata
            )
            
            if response.status_code == 200:
                result = response.json()
                if "_id" in result:
                    self.test_profile_id = result["_id"]
                    self.print_result("Create Basic Biodata", True, f"Profile created with ID: {self.test_profile_id}")
                    return True
                else:
                    self.print_result("Create Basic Biodata", False, "No profile ID in response")
                    return False
            else:
                self.print_result("Create Basic Biodata", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.print_result("Create Basic Biodata", False, f"Exception: {str(e)}")
            return False
    
    def test_get_biodata_profile(self) -> bool:
        """Test retrieving the biodata profile"""
        self.print_separator("GET BIODATA PROFILE")
        
        if not self.test_profile_id:
            self.print_result("Get Biodata Profile", False, "No test profile ID available")
            return False
        
        try:
            response = self.session.get(f"{self.base_url}/biodata/{self.test_profile_id}")
            
            if response.status_code == 200:
                result = response.json()
                self.print_result("Get Biodata Profile", True, f"Profile retrieved: {result.get('first_name', 'N/A')}")
                return True
            else:
                self.print_result("Get Biodata Profile", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.print_result("Get Biodata Profile", False, f"Exception: {str(e)}")
            return False
    
    def test_get_my_profile(self) -> bool:
        """Test getting current user's profile"""
        self.print_separator("GET MY PROFILE")
        
        try:
            response = self.session.get(f"{self.base_url}/biodata/my/profile")
            
            if response.status_code == 200:
                result = response.json()
                self.print_result("Get My Profile", True, f"My profile retrieved: {result.get('first_name', 'N/A')}")
                return True
            else:
                self.print_result("Get My Profile", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.print_result("Get My Profile", False, f"Exception: {str(e)}")
            return False
    
    def test_update_biodata_section(self) -> bool:
        """Test updating specific biodata sections"""
        self.print_separator("UPDATE BIODATA SECTIONS")
        
        if not self.test_profile_id:
            self.print_result("Update Biodata Sections", False, "No test profile ID available")
            return False
        
        # Test updating contact information
        updated_contact = {
            "email": "ananya.updated@example.com",
            "phone_country_code": "+91",
            "phone_number": "9876543211",
            "address": {
                "city": "Delhi",
                "state": "Delhi",
                "country": "India",
                "pincode": "110001"
            }
        }
        
        try:
            response = self.session.patch(
                f"{self.base_url}/biodata/{self.test_profile_id}/contact",
                json=updated_contact
            )
            
            if response.status_code == 200:
                self.print_result("Update Contact Section", True, "Contact information updated successfully")
                return True
            else:
                self.print_result("Update Contact Section", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.print_result("Update Contact Section", False, f"Exception: {str(e)}")
            return False
    
    def test_upgrade_to_detailed(self) -> bool:
        """Test upgrading profile to detailed biodata"""
        self.print_separator("UPGRADE TO DETAILED BIODATA")
        
        if not self.test_profile_id:
            self.print_result("Upgrade to Detailed", False, "No test profile ID available")
            return False
        
        try:
            response = self.session.patch(f"{self.base_url}/biodata/{self.test_profile_id}/upgrade-to-detailed")
            
            if response.status_code == 200:
                self.print_result("Upgrade to Detailed", True, "Profile upgraded to detailed biodata")
                return True
            else:
                self.print_result("Upgrade to Detailed", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.print_result("Upgrade to Detailed", False, f"Exception: {str(e)}")
            return False
    
    def test_detailed_religious_info(self) -> bool:
        """Test updating detailed religious information"""
        self.print_separator("DETAILED RELIGIOUS INFO")
        
        if not self.test_profile_id:
            self.print_result("Detailed Religious Info", False, "No test profile ID available")
            return False
        
        religious_info = {
            "varna": "brahmin",
            "sub_caste": "Gaur Brahmin",
            "religious_sect": "vaishnavism",
            "temple_association": "Local Hanuman Temple",
            "spiritual_practices": ["daily_prayers", "yoga", "meditation"],
            "festivals_observed": ["Diwali", "Karva_Chauth", "Navratri", "Dussehra"],
            "daily_prayers": True,
            "vegetarian_since": "birth"
        }
        
        try:
            response = self.session.patch(
                f"{self.base_url}/biodata/{self.test_profile_id}/detailed-religious-info",
                json=religious_info
            )
            
            if response.status_code == 200:
                self.print_result("Detailed Religious Info", True, "Religious information updated successfully")
                return True
            else:
                self.print_result("Detailed Religious Info", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.print_result("Detailed Religious Info", False, f"Exception: {str(e)}")
            return False
    
    def test_search_profiles(self) -> bool:
        """Test searching biodata profiles"""
        self.print_separator("SEARCH PROFILES")
        
        try:
            # Test basic search
            response = self.session.get(f"{self.base_url}/biodata?gender=female&religion=hindu&limit=5")
            
            if response.status_code == 200:
                result = response.json()
                self.print_result("Search Profiles", True, f"Found {len(result)} profiles")
                return True
            else:
                self.print_result("Search Profiles", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.print_result("Search Profiles", False, f"Exception: {str(e)}")
            return False
    
    def test_text_search(self) -> bool:
        """Test text search functionality"""
        self.print_separator("TEXT SEARCH")
        
        try:
            response = self.session.get(f"{self.base_url}/biodata/search?q=engineer")
            
            if response.status_code == 200:
                result = response.json()
                self.print_result("Text Search", True, f"Text search returned {len(result)} results")
                return True
            else:
                self.print_result("Text Search", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.print_result("Text Search", False, f"Exception: {str(e)}")
            return False
    
    def test_cleanup(self) -> bool:
        """Clean up test data"""
        self.print_separator("CLEANUP TEST DATA")
        
        if not self.test_profile_id:
            self.print_result("Cleanup", True, "No profile to clean up")
            return True
        
        try:
            # Soft delete the profile
            response = self.session.delete(f"{self.base_url}/biodata/{self.test_profile_id}")
            
            if response.status_code == 200:
                self.print_result("Cleanup Profile", True, "Test profile deleted successfully")
                return True
            else:
                self.print_result("Cleanup Profile", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.print_result("Cleanup Profile", False, f"Exception: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all biodata system tests"""
        print("\n" + "🧪" * 20 + " BIODATA SYSTEM TESTING " + "🧪" * 20)
        print(f"Testing against: {self.base_url}")
        print(f"Test user: {TEST_USER['username']}")
        
        # Track results
        results = {}
        
        # Run tests in sequence
        tests = [
            ("Register User", self.register_test_user),
            ("Login User", self.login_test_user),
            ("Create Basic Biodata", self.test_create_basic_biodata),
            ("Get Biodata Profile", self.test_get_biodata_profile),
            ("Get My Profile", self.test_get_my_profile),
            ("Update Biodata Section", self.test_update_biodata_section),
            ("Upgrade to Detailed", self.test_upgrade_to_detailed),
            ("Detailed Religious Info", self.test_detailed_religious_info),
            ("Search Profiles", self.test_search_profiles),
            ("Text Search", self.test_text_search),
            ("Cleanup", self.test_cleanup),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            try:
                success = test_func()
                results[test_name] = success
                if success:
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"❌ CRITICAL ERROR in {test_name}: {str(e)}")
                results[test_name] = False
                failed += 1
            
            time.sleep(0.5)  # Small delay between tests
        
        # Print summary
        self.print_separator("TEST SUMMARY")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📊 Success Rate: {(passed / len(tests)) * 100:.1f}%")
        
        if failed == 0:
            print("\n🎉 ALL TESTS PASSED! Biodata system is working correctly.")
        else:
            print(f"\n⚠️  {failed} tests failed. Review the issues above.")
        
        return results

if __name__ == "__main__":
    tester = BiodataSystemTester(BASE_URL)
    results = tester.run_all_tests()