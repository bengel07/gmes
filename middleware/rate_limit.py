# middleware/rate_limit.py
from functools import wraps
from flask import request, jsonify, g
from datetime import datetime, timedelta
from extensions import db
from models import Partner, RateLimitLog
import redis
import json

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)


def check_rate_limit(partner_id, api_key):
    """Vérifie les limites de taux"""
    partner = Partner.query.get(partner_id)

    if not partner or not partner.is_active:
        return False, "Partner not active"

    now = datetime.utcnow()

    # Clés Redis pour les compteurs
    minute_key = f"rate_limit:{partner_id}:minute:{now.strftime('%Y%m%d%H%M')}"
    hour_key = f"rate_limit:{partner_id}:hour:{now.strftime('%Y%m%d%H')}"
    day_key = f"rate_limit:{partner_id}:day:{now.strftime('%Y%m%d')}"

    # Incrémenter les compteurs
    minute_count = redis_client.incr(minute_key)
    hour_count = redis_client.incr(hour_key)
    day_count = redis_client.incr(day_key)

    # Définir les TTL
    if minute_count == 1:
        redis_client.expire(minute_key, 60)
    if hour_count == 1:
        redis_client.expire(hour_key, 3600)
    if day_count == 1:
        redis_client.expire(day_key, 86400)

    # Vérifier les limites
    if minute_count > partner.rate_limit_per_minute:
        log_rate_limit(partner.id, api_key, f"Minute limit exceeded: {minute_count}/{partner.rate_limit_per_minute}")
        return False, f"Rate limit exceeded. Max {partner.rate_limit_per_minute} requests per minute."

    if hour_count > partner.rate_limit_per_hour:
        log_rate_limit(partner.id, api_key, f"Hour limit exceeded: {hour_count}/{partner.rate_limit_per_hour}")
        return False, f"Rate limit exceeded. Max {partner.rate_limit_per_hour} requests per hour."

    if day_count > partner.rate_limit_per_day:
        log_rate_limit(partner.id, api_key, f"Day limit exceeded: {day_count}/{partner.rate_limit_per_day}")
        return False, f"Rate limit exceeded. Max {partner.rate_limit_per_day} requests per day."

    return True, None


def log_rate_limit(partner_id, api_key, reason):
    """Log une violation de rate limit"""
    log = RateLimitLog(
        partner_id=partner_id,
        api_key=api_key,
        endpoint=request.endpoint or request.path,
        method=request.method,
        ip_address=request.remote_addr,
        was_blocked=True,
        reason=reason
    )
    db.session.add(log)
    db.session.commit()


def rate_limit_required(f):
    """Décorateur pour appliquer le rate limit"""

    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')

        if not api_key:
            return jsonify({'error': 'API Key required'}), 401

        # Trouver le partenaire par API key
        partner = Partner.query.filter_by(api_key=api_key, is_active=True).first()

        if not partner:
            return jsonify({'error': 'Invalid API Key'}), 401

        # Vérifier le rate limit
        allowed, message = check_rate_limit(partner.id, api_key)

        if not allowed:
            return jsonify({'error': message}), 429

        g.partner = partner
        g.api_key = api_key

        return f(*args, **kwargs)

    return decorated