import requests
import sys
import json
from datetime import datetime

class SuperchargerAPITester:
    def __init__(self, base_url="https://supermap-tesla.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def run_test(self, name, method, endpoint, expected_status, data=None, validate_response=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)

            success = response.status_code == expected_status
            response_data = {}
            
            try:
                response_data = response.json() if response.text else {}
            except:
                response_data = {"raw_response": response.text}

            if success:
                # Additional validation if provided
                if validate_response and response_data:
                    validation_result = validate_response(response_data)
                    if not validation_result:
                        success = False
                        print(f"❌ Failed - Response validation failed")
                    else:
                        print(f"✅ Passed - Status: {response.status_code}, Validation: OK")
                else:
                    print(f"✅ Passed - Status: {response.status_code}")
                
                if success:
                    self.tests_passed += 1
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                if response.text:
                    print(f"   Response: {response.text[:200]}...")

            self.test_results.append({
                "name": name,
                "method": method,
                "endpoint": endpoint,
                "expected_status": expected_status,
                "actual_status": response.status_code,
                "success": success,
                "response_data": response_data
            })

            return success, response_data

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.test_results.append({
                "name": name,
                "method": method,
                "endpoint": endpoint,
                "expected_status": expected_status,
                "actual_status": "ERROR",
                "success": False,
                "error": str(e)
            })
            return False, {}

    def test_root_endpoint(self):
        """Test API root endpoint"""
        return self.run_test(
            "API Root",
            "GET",
            "",
            200,
            validate_response=lambda r: "message" in r
        )

    def test_get_all_superchargers(self):
        """Test getting all superchargers"""
        def validate_superchargers(response_data):
            if not isinstance(response_data, list):
                print(f"   Expected list, got {type(response_data)}")
                return False
            if len(response_data) != 12:
                print(f"   Expected 12 superchargers, got {len(response_data)}")
                return False
            
            # Check first supercharger structure
            if response_data:
                sc = response_data[0]
                required_fields = ['id', 'name', 'location', 'stalls', 'available', 'power', 'amenities']
                for field in required_fields:
                    if field not in sc:
                        print(f"   Missing required field: {field}")
                        return False
                
                # Check location structure
                if 'lat' not in sc['location'] or 'lng' not in sc['location']:
                    print(f"   Invalid location structure")
                    return False
                    
                print(f"   Found {len(response_data)} superchargers with valid structure")
            return True

        return self.run_test(
            "Get All Superchargers",
            "GET",
            "superchargers",
            200,
            validate_response=validate_superchargers
        )

    def test_get_specific_supercharger(self, supercharger_id):
        """Test getting a specific supercharger"""
        def validate_single_supercharger(response_data):
            if not isinstance(response_data, dict):
                print(f"   Expected dict, got {type(response_data)}")
                return False
            
            required_fields = ['id', 'name', 'location', 'stalls', 'available', 'power', 'amenities', 'address', 'city', 'state']
            for field in required_fields:
                if field not in response_data:
                    print(f"   Missing required field: {field}")
                    return False
            
            if response_data['id'] != supercharger_id:
                print(f"   ID mismatch: expected {supercharger_id}, got {response_data['id']}")
                return False
                
            print(f"   Supercharger details valid: {response_data['name']}")
            return True

        return self.run_test(
            f"Get Supercharger by ID",
            "GET",
            f"superchargers/{supercharger_id}",
            200,
            validate_response=validate_single_supercharger
        )

    def test_get_nonexistent_supercharger(self):
        """Test getting a non-existent supercharger"""
        return self.run_test(
            "Get Non-existent Supercharger",
            "GET",
            "superchargers/nonexistent-id",
            404
        )

    def test_plan_trip(self):
        """Test trip planning"""
        trip_data = {
            "origin": {"lat": 37.7749, "lng": -122.4194},  # San Francisco
            "destination": {"lat": 34.0522, "lng": -118.2437},  # Los Angeles
            "vehicleModel": "Model 3 Long Range",
            "currentCharge": 80
        }

        def validate_trip_plan(response_data):
            if not isinstance(response_data, dict):
                print(f"   Expected dict, got {type(response_data)}")
                return False
            
            required_fields = ['id', 'origin', 'destination', 'vehicleModel', 'currentCharge', 'stops', 'totalDistance', 'totalTime']
            for field in required_fields:
                if field not in response_data:
                    print(f"   Missing required field: {field}")
                    return False
            
            # Validate stops structure
            if not isinstance(response_data['stops'], list):
                print(f"   Stops should be a list")
                return False
            
            for stop in response_data['stops']:
                stop_fields = ['superchargerId', 'arrivalCharge', 'departureCharge', 'chargingTime', 'name', 'location']
                for field in stop_fields:
                    if field not in stop:
                        print(f"   Missing stop field: {field}")
                        return False
            
            print(f"   Trip planned successfully: {len(response_data['stops'])} stops, {response_data['totalDistance']:.0f}km")
            return True

        return self.run_test(
            "Plan Trip",
            "POST",
            "trips/plan",
            200,
            data=trip_data,
            validate_response=validate_trip_plan
        )

    def test_plan_trip_invalid_data(self):
        """Test trip planning with invalid data"""
        invalid_trip_data = {
            "origin": {"lat": "invalid", "lng": -122.4194},
            "destination": {"lat": 34.0522, "lng": -118.2437},
            "vehicleModel": "Model 3 Long Range",
            "currentCharge": 80
        }

        return self.run_test(
            "Plan Trip - Invalid Data",
            "POST",
            "trips/plan",
            422  # Validation error
        )

    def test_vehicle_profile_endpoints(self):
        """Test vehicle profile save and get"""
        profile_data = {
            "vehicleModel": "Model S",
            "batteryCapacity": 100,
            "currentCharge": 75
        }

        # Test saving profile
        save_success, save_response = self.run_test(
            "Save Vehicle Profile",
            "POST",
            "vehicle-profile",
            200,
            data=profile_data,
            validate_response=lambda r: r.get('vehicleModel') == 'Model S'
        )

        # Test getting profile
        get_success, get_response = self.run_test(
            "Get Vehicle Profile",
            "GET",
            "vehicle-profile?userId=default_user",
            200,
            validate_response=lambda r: 'vehicleModel' in r and 'batteryCapacity' in r
        )

        return save_success and get_success

def main():
    print("🚗 Tesla Supercharger Network API Testing")
    print("=" * 50)
    
    tester = SuperchargerAPITester()
    
    # Test API root
    tester.test_root_endpoint()
    
    # Test supercharger endpoints
    success, superchargers_data = tester.test_get_all_superchargers()
    
    # Test specific supercharger if we got data
    if success and superchargers_data:
        first_supercharger_id = superchargers_data[0]['id']
        tester.test_get_specific_supercharger(first_supercharger_id)
    
    # Test non-existent supercharger
    tester.test_get_nonexistent_supercharger()
    
    # Test trip planning
    tester.test_plan_trip()
    tester.test_plan_trip_invalid_data()
    
    # Test vehicle profile
    tester.test_vehicle_profile_endpoints()
    
    # Print final results
    print(f"\n📊 Test Results Summary")
    print("=" * 50)
    print(f"Tests Run: {tester.tests_run}")
    print(f"Tests Passed: {tester.tests_passed}")
    print(f"Success Rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    # Print failed tests
    failed_tests = [t for t in tester.test_results if not t['success']]
    if failed_tests:
        print(f"\n❌ Failed Tests ({len(failed_tests)}):")
        for test in failed_tests:
            print(f"   - {test['name']}: {test.get('error', f'Status {test.get(\"actual_status\", \"unknown\")}')}")
    
    # Save detailed results
    with open('/app/backend_test_results.json', 'w') as f:
        json.dump({
            'summary': {
                'tests_run': tester.tests_run,
                'tests_passed': tester.tests_passed,
                'success_rate': (tester.tests_passed/tester.tests_run)*100,
                'timestamp': datetime.now().isoformat()
            },
            'detailed_results': tester.test_results
        }, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: /app/backend_test_results.json")
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())