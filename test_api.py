#!/usr/bin/env python3
"""
Test script for CLF Analysis API
Tests all endpoints to ensure the API is working correctly
"""
import requests
import json
import sys
import time

# API base URL
BASE_URL = "http://localhost:6300"

def print_section(title):
    """Print a section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_health_check():
    """Test the health check endpoint"""
    print_section("Testing Health Check")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ Health check PASSED")
            return True
        else:
            print("❌ Health check FAILED")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API. Is the service running?")
        print("   Try: docker-compose up -d clf-analysis-api")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_root_endpoint():
    """Test the root endpoint"""
    print_section("Testing Root Endpoint")
    
    try:
        response = requests.get(BASE_URL, timeout=5)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ Root endpoint PASSED")
            return True
        else:
            print("❌ Root endpoint FAILED")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_analysis_missing_build_id():
    """Test analysis endpoint with missing build_id"""
    print_section("Testing Analysis - Missing build_id")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/analyze",
            json={},
            timeout=5
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 400:
            print("✅ Validation PASSED (correctly rejected missing build_id)")
            return True
        else:
            print("❌ Validation FAILED (should return 400)")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_analysis_with_build_id(build_id="271360"):
    """Test analysis endpoint with a valid build_id"""
    print_section(f"Testing Analysis - Build ID: {build_id}")
    
    print("⚠️  WARNING: This test will run an actual analysis!")
    print(f"   Build ID: {build_id}")
    print(f"   This may take several minutes...")
    
    user_input = input("\nDo you want to proceed? (yes/no): ").strip().lower()
    if user_input not in ['yes', 'y']:
        print("⏭️  Skipping analysis test")
        return None
    
    try:
        print("\n🔄 Starting analysis... (this may take a while)")
        start_time = time.time()
        
        response = requests.post(
            f"{BASE_URL}/api/analyze",
            json={
                "build_id": build_id,
                "holes_interval": 10,
                "create_composite_views": False
            },
            timeout=600  # 10 minute timeout
        )
        
        elapsed_time = time.time() - start_time
        
        print(f"\n⏱️  Analysis completed in {elapsed_time:.2f} seconds")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200 and response.json().get('status') == 'success':
            print(f"✅ Analysis PASSED")
            result = response.json().get('result', {})
            if result.get('output_dir'):
                print(f"   Output directory: {result['output_dir']}")
            if result.get('summary_path'):
                print(f"   Summary file: {result['summary_path']}")
            return True
        else:
            print(f"❌ Analysis FAILED")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out (analysis took too long)")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_analysis_by_url(build_id="271360"):
    """Test analysis endpoint with build_id in URL"""
    print_section(f"Testing Analysis by URL - Build ID: {build_id}")
    
    print("⚠️  WARNING: This test will run an actual analysis!")
    print(f"   Build ID: {build_id}")
    print(f"   Endpoint: POST /api/builds/{build_id}/analyze")
    
    user_input = input("\nDo you want to proceed? (yes/no): ").strip().lower()
    if user_input not in ['yes', 'y']:
        print("⏭️  Skipping URL analysis test")
        return None
    
    try:
        print("\n🔄 Starting analysis... (this may take a while)")
        start_time = time.time()
        
        response = requests.post(
            f"{BASE_URL}/api/builds/{build_id}/analyze",
            json={
                "holes_interval": 15
            },
            timeout=600  # 10 minute timeout
        )
        
        elapsed_time = time.time() - start_time
        
        print(f"\n⏱️  Analysis completed in {elapsed_time:.2f} seconds")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200 and response.json().get('status') == 'success':
            print(f"✅ URL Analysis PASSED")
            return True
        else:
            print(f"❌ URL Analysis FAILED")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out (analysis took too long)")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  CLF Analysis API Test Suite")
    print("="*60)
    print(f"\nTesting API at: {BASE_URL}")
    
    results = {
        "Health Check": test_health_check(),
        "Root Endpoint": test_root_endpoint(),
        "Validation (Missing build_id)": test_analysis_missing_build_id(),
    }
    
    # Only run analysis tests if basic tests pass
    if all(results.values()):
        print("\n✅ All basic tests passed!")
        print("\n📝 Optional: Test actual analysis (may take several minutes)")
        
        # Get build_id from user
        build_id = input("\nEnter build_id to test (or press Enter to skip): ").strip()
        
        if build_id:
            results["Analysis (POST with JSON)"] = test_analysis_with_build_id(build_id)
            
            # Only test URL endpoint if user wants to continue
            if results["Analysis (POST with JSON)"]:
                print("\nTest URL endpoint as well?")
                results["Analysis (POST by URL)"] = test_analysis_by_url(build_id)
    
    # Print summary
    print_section("Test Summary")
    
    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)
    total = len(results)
    
    for test_name, result in results.items():
        if result is True:
            status = "✅ PASSED"
        elif result is False:
            status = "❌ FAILED"
        else:
            status = "⏭️  SKIPPED"
        print(f"{test_name:.<45} {status}")
    
    print(f"\n{'='*60}")
    print(f"Total: {total} | Passed: {passed} | Failed: {failed} | Skipped: {skipped}")
    print(f"{'='*60}\n")
    
    if failed > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
