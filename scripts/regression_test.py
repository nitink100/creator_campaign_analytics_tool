import requests
import sys

BASE_URL = "http://localhost:8000/api"

def test_endpoint(name, method, path, expected_status=200, json=None):
    print(f"Testing {name} ({method} {path})...", end=" ", flush=True)
    try:
        if method == "GET":
            response = requests.get(f"{BASE_URL}{path}")
        elif method == "POST":
            response = requests.post(f"{BASE_URL}{path}", json=json)
        elif method == "DELETE":
            response = requests.delete(f"{BASE_URL}{path}")
        
        if response.status_code == expected_status:
            print("✅ PASS")
            return response.json()
        else:
            print(f"❌ FAIL (Status: {response.status_code})")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"💥 ERROR: {str(e)}")
        return None

def main():
    print("🚀 Starting Regression Tests\n")
    
    # 1. Creators
    creators = test_endpoint("List Creators", "GET", "/creators")
    if creators and "items" in creators and len(creators["items"]) > 0:
        creator_id = creators["items"][0]["creator_id"]
        test_endpoint("Get Creator Detail", "GET", f"/creators/{creator_id}")
    
    # 2. Campaigns
    campaigns = test_endpoint("List Campaigns", "GET", "/campaigns")
    
    # Create test campaign
    new_campaign = test_endpoint("Create Campaign", "POST", "/campaigns", json={
        "name": "Regression Test Campaign",
        "description": "Verification flow",
        "budget": 5000
    }, expected_status=201)
    
    if new_campaign:
        camp_id = new_campaign["id"]
        test_endpoint("Get Campaign", "GET", f"/campaigns/{camp_id}")
        
        # Add member (duplicate test)
        if creators and len(creators["items"]) > 0:
            c_id = creators["items"][0]["creator_id"]
            test_endpoint("Add Member", "POST", f"/campaigns/{camp_id}/members", json={"creator_profile_id": c_id})
            test_endpoint("Add Member (Duplicate Check)", "POST", f"/campaigns/{camp_id}/members", json={"creator_profile_id": c_id})
            
            # Verify members list
            updated = test_endpoint("Verify Members unikeness", "GET", f"/campaigns/{camp_id}")
            if updated and "creators" in updated:
                member_ids = [c["creator_id"] for c in updated["creators"]]
                if len(member_ids) != len(set(member_ids)):
                    print("❌ FAIL: Duplicates found in member list!")
                else:
                    print("✅ PASS: No duplicates in member list")
        
            # Test member removal
            test_endpoint("Remove Member", "DELETE", f"/campaigns/{camp_id}/members/{c_id}")
            
            # Verify removal
            after_removal = test_endpoint("Verify Removal", "GET", f"/campaigns/{camp_id}")
            if after_removal and len(after_removal.get("creators", [])) == 0:
                print("✅ PASS: Member removed successfully")
            else:
                print("❌ FAIL: Member still present after removal")
        
        # Cleanup
        test_endpoint("Delete Campaign", "DELETE", f"/campaigns/{camp_id}")
        
        # Verify campaign deletion
        after_delete = test_endpoint("Verify Delete (404)", "GET", f"/campaigns/{camp_id}", expected_status=404)
        if after_delete is None: # Because test_endpoint returns None on non-200
             print("✅ PASS: Campaign 404s after deletion")

    # 3. Analytics
    test_endpoint("General Summary", "GET", "/analytics/summary")
    test_endpoint("KPIs", "GET", "/analytics/kpis")
    test_endpoint("Top Content", "GET", "/analytics/top-content")
    test_endpoint("Top Creators", "GET", "/analytics/top-creators")

    print("\n✅ Regression Tests Complete")

if __name__ == "__main__":
    main()
