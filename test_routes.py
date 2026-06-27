import requests

url = "http://127.0.0.1:5000/api/partner/admin/partners"

headers = {
    "Content-Type": "application/json"
}

body = {
    "name": "GMES Microcredit",
    "permissions": {
        "can_create_payment": True,
        "can_check_balance": True
    },
    "webhook_url": "https://example.com/webhook"
}

r = requests.post(url, json=body, headers=headers)

print("STATUS:", r.status_code)
print("TEXT:", r.text)