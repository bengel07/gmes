import requests

BASE_URL = "http://127.0.0.1:5000"

url = f"{BASE_URL}/api/partner/admin/partners"

payload = {
    "name": "GMES Microcredit",
    "permissions": ["TRANSFER", "BALANCE"],
    "webhook_url": "https://example.com/webhook"
}

headers = {
    "Content-Type": "application/json"
}

print("URL:", url)

try:
    response = requests.post(url, json=payload, headers=headers)

    print("STATUS:", response.status_code)
    print("TEXT:", response.text)

except Exception as e:
    print("ERROR:", str(e))