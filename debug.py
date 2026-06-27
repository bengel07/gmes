import requests

BASE_URL = "http://127.0.0.1:5000"

print("=== LOGIN TEST ===")

login_payload = {
    "email": "contactbegingeler@gmail.com",
    "password": "A-dminB123"
}

r = requests.post(f"{BASE_URL}/api/auth/login", json=login_payload)

print("STATUS:", r.status_code)
print("RESPONSE:", r.text)

if r.status_code == 200:
    token = r.json().get("access_token")

    print("\n=== TOKEN TEST ===")
    print("TOKEN:", token[:50], "...")

    headers = {
        "Authorization": f"Bearer {token}"
    }

    r2 = requests.get(
        f"{BASE_URL}/api/partner/admin/partners",
        headers=headers
    )

    print("\nSTATUS:", r2.status_code)
    print("RESPONSE:", r2.text)