import requests
import sys
import os
import traceback

BASE_URL = "http://127.0.0.1:5000"


def print_header(title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def test_endpoint(path, method="GET", data=None):
    url = BASE_URL + path
    try:
        if method == "GET":
            r = requests.get(url)
        else:
            r = requests.post(url, json=data)

        print(f"\n[{method}] {url}")
        print("STATUS:", r.status_code)
        print("RESPONSE:", r.text[:300])

    except Exception as e:
        print(f"[ERROR] {url}")
        print(str(e))


def check_server_alive():
    print_header("1. SERVER CHECK")
    try:
        r = requests.get(BASE_URL)
        print("Server reachable:", r.status_code)
    except Exception as e:
        print("Server NOT reachable:", e)


def scan_routes():
    print_header("2. FLASK ROUTES CHECK VIA DEBUG ENDPOINT")

    # test common routes
    routes_to_test = [
        "/",
        "/ping",
        "/debug",
        "/api/partner/admin/partners",
        "/api/admin/partners",
        "/partners"
    ]

    for r in routes_to_test:
        test_endpoint(r)


def test_partner_post():
    print_header("3. PARTNER CREATE TEST")

    payload = {
        "name": "GMES Microcredit",
        "permissions": ["TRANSFER", "BALANCE"],
        "webhook_url": "https://example.com/webhook"
    }

    test_endpoint("/api/partner/admin/partners", "POST", payload)


def system_info():
    print_header("4. SYSTEM INFO")

    print("Python version:", sys.version)
    print("Current directory:", os.getcwd())

    print("\nFiles in project root:")
    for f in os.listdir("."):
        print("-", f)


def main():
    try:
        system_info()
        check_server_alive()
        scan_routes()
        test_partner_post()

    except Exception:
        print("\nFATAL ERROR:")
        print(traceback.format_exc())


if __name__ == "__main__":
    main()