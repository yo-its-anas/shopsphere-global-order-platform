import os
import sys
import json
import urllib.request
import urllib.parse
from time import sleep

KC_ADMIN = "admin"
KC_PASS = "admin"
KC_URL = "http://localhost:8080"
GATEWAY_URL = "http://localhost:8000"

def get_admin_token():
    req = urllib.request.Request(
        f"{KC_URL}/realms/master/protocol/openid-connect/token",
        data=urllib.parse.urlencode({
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": KC_ADMIN,
            "password": KC_PASS,
        }).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.load(resp)["access_token"]
    except urllib.error.HTTPError as e:
        print(f"Failed to get admin token: {e.read().decode()}")
        raise

def create_user(admin_token, username, role):
    # 1. Create user
    req = urllib.request.Request(
        f"{KC_URL}/admin/realms/shopsphere/users",
        data=json.dumps({
            "username": username,
            "enabled": True,
            "credentials": [{"type": "password", "value": "test1234", "temporary": False}]
        }).encode(),
        headers={"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            pass
    except urllib.error.HTTPError as e:
        if e.code != 409: # Ignore conflict if already exists
            raise

    # 2. Get user ID
    req = urllib.request.Request(
        f"{KC_URL}/admin/realms/shopsphere/users?username={username}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    with urllib.request.urlopen(req) as resp:
        user_id = json.load(resp)[0]["id"]

    # 3. Get role ID
    req = urllib.request.Request(
        f"{KC_URL}/admin/realms/shopsphere/roles/{role}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    with urllib.request.urlopen(req) as resp:
        role_data = json.load(resp)
        
    # 4. Assign role
    req = urllib.request.Request(
        f"{KC_URL}/admin/realms/shopsphere/users/{user_id}/role-mappings/realm",
        data=json.dumps([role_data]).encode(),
        headers={"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        pass

def get_user_token(username):
    req = urllib.request.Request(
        f"{KC_URL}/realms/shopsphere/protocol/openid-connect/token",
        data=urllib.parse.urlencode({
            "grant_type": "password",
            "client_id": "shopsphere-spa",
            "username": username,
            "password": "test1234",
        }).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)["access_token"]

def main():
    admin_token = get_admin_token()
    create_user(admin_token, "test-customer", "customer")
    create_user(admin_token, "test-ops", "operations_admin")
    
    customer_token = get_user_token("test-customer")
    ops_token = get_user_token("test-ops")

    print("[INFO] Testing unauthorized customer access...")
    try:
        req = urllib.request.Request(
            f"{GATEWAY_URL}/api/v1/operations/dashboard",
            headers={"Authorization": f"Bearer {customer_token}"}
        )
        urllib.request.urlopen(req)
        print("[ERROR] Customer access was not rejected!")
        sys.exit(1)
    except urllib.error.HTTPError as e:
        if e.code in [401, 403]:
            print("[OK] Customer access successfully rejected.")
        else:
            print(f"[ERROR] Unexpected status code {e.code}")
            sys.exit(1)

    print("[INFO] Testing operations_admin dashboard access...")
    req = urllib.request.Request(
        f"{GATEWAY_URL}/api/v1/operations/dashboard",
        headers={"Authorization": f"Bearer {ops_token}"}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.load(resp)
            print("[OK] operations_admin successfully retrieved dashboard data.")
            print(json.dumps(data, indent=2))
            
            # Check for real business/operations data
            if "system_performance" in data and "services_health" in data:
                print("[OK] Real dashboard structures detected.")
            else:
                print("[ERROR] Dashboard structure invalid.")
                sys.exit(1)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"[ERROR] Failed to retrieve dashboard: {e.code} - {error_body}")
        sys.exit(1)
        
    print("[INFO] Testing executive business KPI dashboard access...")
    req = urllib.request.Request(
        f"{GATEWAY_URL}/api/v1/dashboard/summary",
        headers={"Authorization": f"Bearer {ops_token}"}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.load(resp)
            print("[OK] Executive business data retrieved.")
            print(json.dumps(data, indent=2))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"[ERROR] Failed to retrieve business KPIs: {e.code} - {error_body}")
        sys.exit(1)

if __name__ == "__main__":
    main()
