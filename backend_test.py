import requests
import sys
import json
from datetime import datetime

class FigmaAPITester:
    def __init__(self, base_url=""):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.saved_request_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        request_headers = {'Content-Type': 'application/json'}
        if headers:
            request_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        print(f"   Method: {method}")
        if data:
            print(f"   Data: {json.dumps(data, indent=2)}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=request_headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=request_headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=request_headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=request_headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
                    return True, response_data
                except:
                    return True, response.text
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_saved_requests_crud(self):
        """Test CRUD operations for saved requests"""
        print("\n" + "="*50)
        print("TESTING SAVED REQUESTS CRUD")
        print("="*50)
        
        # Test GET saved requests (should be empty initially)
        success, data = self.run_test(
            "Get Saved Requests (Empty)",
            "GET",
            "saved-requests",
            200
        )
        
        # Test POST create saved request
        test_request = {
            "name": "Test Get File",
            "method": "GET",
            "endpoint": "/files/test-file-key",
            "headers": {"X-Figma-Token": "test-token"},
            "body": None,
            "category": "Files",
            "is_favorite": False
        }
        
        success, data = self.run_test(
            "Create Saved Request",
            "POST",
            "saved-requests",
            200,
            data=test_request
        )
        
        if success and data.get('id'):
            self.saved_request_id = data['id']
            print(f"   Created request with ID: {self.saved_request_id}")
        
        # Test GET saved requests (should have one now)
        success, data = self.run_test(
            "Get Saved Requests (With Data)",
            "GET",
            "saved-requests",
            200
        )
        
        # Test PUT update saved request
        if self.saved_request_id:
            update_data = {
                "name": "Updated Test Request",
                "is_favorite": True
            }
            
            success, data = self.run_test(
                "Update Saved Request",
                "PUT",
                f"saved-requests/{self.saved_request_id}",
                200,
                data=update_data
            )
        
        # Test DELETE saved request
        if self.saved_request_id:
            success, data = self.run_test(
                "Delete Saved Request",
                "DELETE",
                f"saved-requests/{self.saved_request_id}",
                200
            )

    def test_request_history(self):
        """Test request history endpoints"""
        print("\n" + "="*50)
        print("TESTING REQUEST HISTORY")
        print("="*50)
        
        # Test GET request history (should be empty initially)
        success, data = self.run_test(
            "Get Request History (Empty)",
            "GET",
            "request-history",
            200
        )
        
        # Test DELETE clear history
        success, data = self.run_test(
            "Clear Request History",
            "DELETE",
            "request-history",
            200
        )

    def test_figma_proxy(self):
        """Test Figma API proxy endpoint"""
        print("\n" + "="*50)
        print("TESTING FIGMA PROXY")
        print("="*50)
        
        # Test proxy with invalid token (should fail but endpoint should work)
        proxy_request = {
            "method": "GET",
            "endpoint": "/me",
            "headers": {
                "X-Figma-Token": "invalid-token-for-testing"
            },
            "body": None
        }
        
        # This should return 200 from our proxy but with error from Figma API
        success, data = self.run_test(
            "Figma Proxy (Invalid Token)",
            "POST",
            "figma/proxy",
            200,
            data=proxy_request
        )
        
        # The response should contain status_code and data fields
        if success:
            if 'status_code' in data and 'data' in data:
                print("✅ Proxy response structure is correct")
            else:
                print("❌ Proxy response structure is incorrect")

    def test_error_cases(self):
        """Test error handling"""
        print("\n" + "="*50)
        print("TESTING ERROR CASES")
        print("="*50)
        
        # Test invalid saved request ID
        success, data = self.run_test(
            "Get Non-existent Saved Request",
            "DELETE",
            "saved-requests/invalid-id",
            404
        )
        
        # Test invalid method for proxy
        invalid_proxy = {
            "method": "INVALID",
            "endpoint": "/me",
            "headers": {"X-Figma-Token": "test"},
            "body": None
        }
        
        success, data = self.run_test(
            "Figma Proxy (Invalid Method)",
            "POST",
            "figma/proxy",
            400,
            data=invalid_proxy
        )

def main():
    print("🚀 Starting Figma API Playground Backend Tests")
    print("=" * 60)
    
    tester = FigmaAPITester()
    
    # Run all test suites
    tester.test_saved_requests_crud()
    tester.test_request_history()
    tester.test_figma_proxy()
    tester.test_error_cases()
    
    # Print final results
    print("\n" + "="*60)
    print("📊 FINAL TEST RESULTS")
    print("="*60)
    print(f"Tests run: {tester.tests_run}")
    print(f"Tests passed: {tester.tests_passed}")
    print(f"Tests failed: {tester.tests_run - tester.tests_passed}")
    print(f"Success rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())