# debug_token.py
import requests
import json

BASE_URL = "http://127.0.0.1:5000"


def test_login():
    print("=" * 50)
    print("1. TEST DE CONNEXION")
    print("=" * 50)

    # Tenter de se connecter
    login_data = {
        "email": "contactbegingeler@gmail.com",
        "password": "A-dminB123"
    }

    # Essayer différentes routes
    routes = [
        "/login",
        "/api/login",
        "/api/auth/login"
    ]

    for route in routes:
        try:
            print(f"\n🔍 Test route: {route}")
            response = requests.post(f"{BASE_URL}{route}", json=login_data)
            print(f"   Statut: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"   Réponse: {json.dumps(data, indent=2)[:500]}")

                if 'access_token' in data or 'token' in data:
                    token = data.get('access_token') or data.get('token')
                    print(f"   ✅ TOKEN TROUVÉ: {token[:50]}...")
                    return token
                elif 'success' in data and data['success']:
                    print(f"   ✅ Connexion réussie mais pas de token")
            else:
                print(f"   ❌ Erreur: {response.text[:200]}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")

    return None


def test_dashboard(token):
    print("\n" + "=" * 50)
    print("2. TEST DASHBOARD AVEC TOKEN")
    print("=" * 50)

    if not token:
        print("❌ Pas de token à tester")
        return

    # Tester avec header Authorization
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(f"{BASE_URL}/dashboard", headers=headers)
        print(f"Statut: {response.status_code}")

        if response.status_code == 200:
            print("✅ Dashboard accessible")
        else:
            print(f"❌ Redirection vers: {response.headers.get('Location')}")
    except Exception as e:
        print(f"❌ Erreur: {e}")


def test_session():
    print("\n" + "=" * 50)
    print("3. VÉRIFICATION SESSION FLASK")
    print("=" * 50)

    try:
        # D'abord se connecter pour avoir une session
        login_data = {
            "email": "contactbegingeler@gmail.com",
            "password": "A-dminB123"
        }

        session = requests.Session()
        response = session.post(f"{BASE_URL}/login", json=login_data)

        if response.status_code == 200:
            # Maintenant vérifier la session
            check = session.get(f"{BASE_URL}/api/check-session")
            print(f"Session: {check.json() if check.ok else 'Non disponible'}")
    except Exception as e:
        print(f"❌ Erreur: {e}")


def test_api_admin(token):
    print("\n" + "=" * 50)
    print("4. TEST API ADMIN")
    print("=" * 50)

    if not token:
        print("❌ Pas de token")
        return

    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(f"{BASE_URL}/api/admin/users", headers=headers)
        print(f"API /api/admin/users - Statut: {response.status_code}")

        if response.status_code == 200:
            users = response.json()
            print(f"✅ {len(users)} utilisateurs trouvés")
        else:
            print(f"❌ Erreur: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Erreur: {e}")


def simulate_frontend():
    print("\n" + "=" * 50)
    print("5. SIMULATION FRONTEND")
    print("=" * 50)

    # 1. Login
    login_data = {
        "email": "contactbegingeler@gmail.com",
        "password": "A-dminB123"
    }

    response = requests.post(f"{BASE_URL}/login", json=login_data)

    if response.status_code == 200:
        data = response.json()

        # 2. Extraire token
        token = data.get('access_token') or data.get('token')

        if token:
            print(f"✅ Token reçu: {token[:50]}...")

            # 3. Stocker (simuler localStorage)
            print("✅ Token stocké (simulé)")

            # 4. Faire requête avec token
            headers = {"Authorization": f"Bearer {token}"}
            dashboard_resp = requests.get(f"{BASE_URL}/dashboard", headers=headers)
            print(f"Dashboard avec token: {dashboard_resp.status_code}")

            admin_resp = requests.get(f"{BASE_URL}/admin/dashboard", headers=headers)
            print(f"Admin dashboard avec token: {admin_resp.status_code}")

        else:
            print("❌ Pas de token dans la réponse")
            print(f"Réponse: {data}")
    else:
        print(f"❌ Login échoué: {response.status_code}")
        print(f"Réponse: {response.text}")


if __name__ == "__main__":
    print("\n🔍 DIAGNOSTIC GMESPAY\n")

    # Tester connexion et récupérer token
    token = test_login()

    # Tester dashboard avec token
    test_dashboard(token)

    # Tester session
    test_session()

    # Tester API admin
    test_api_admin(token)

    # Simulation frontend complet
    simulate_frontend()

    print("\n" + "=" * 50)
    print("DIAGNOSTIC TERMINÉ")
    print("=" * 50)