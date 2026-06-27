# services/exchange_service.py
from extensions import db
from models import ExchangeRate
from datetime import datetime
import requests
from flask import current_app


def get_current_usd_to_htg_rate():
    """Obtenir le taux de change actuel USD -> HTG"""
    # Essayer de récupérer depuis la base de données
    latest_rate = ExchangeRate.query.order_by(ExchangeRate.created_at.desc()).first()

    if latest_rate:
        return float(latest_rate.usd_to_htg)

    # Taux par défaut (à remplacer par API réelle)
    return 130.0  # 1 USD = 130 HTG (approx)


def convert_htg_to_usd(amount_htg):
    """Convertir HTG en USD"""
    rate = get_current_usd_to_htg_rate()
    return amount_htg / rate


def convert_usd_to_htg(amount_usd):
    """Convertir USD en HTG"""
    rate = get_current_usd_to_htg_rate()
    return amount_usd * rate


def update_exchange_rate(usd_to_htg):
    """Mettre à jour le taux de change en base"""
    rate = ExchangeRate(usd_to_htg=usd_to_htg)
    db.session.add(rate)
    db.session.commit()
    return rate


def fetch_live_exchange_rate():
    """Récupérer le taux de change depuis une API externe"""
    try:
        # Utiliser une API gratuite (exemple: exchangerate-api.com)
        url = current_app.config.get('EXCHANGE_RATE_API_URL', 'https://api.exchangerate-api.com/v4/latest/USD')
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            data = response.json()
            # HTG n'est pas toujours disponible, utiliser une approximation
            usd_to_htg = data.get('rates', {}).get('HTG', 130.0)
            update_exchange_rate(usd_to_htg)
            return usd_to_htg
    except Exception as e:
        current_app.logger.error(f"Failed to fetch exchange rate: {e}")

    return get_current_usd_to_htg_rate()