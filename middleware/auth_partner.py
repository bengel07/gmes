from flask import request, jsonify
from utils.security import verify_partner

def partner_required(permission=None):
    def decorator(func):
        def wrapper(*args, **kwargs):
            client_id = request.headers.get("X-CLIENT-ID")
            client_secret = request.headers.get("X-CLIENT-SECRET")

            partner = verify_partner(client_id, client_secret)

            if not partner:
                return jsonify({"error": "Unauthorized"}), 401

            if not partner.is_active:
                return jsonify({"error": "Partner disabled"}), 403

            if permission and permission not in partner.permissions:
                return jsonify({"error": "Permission denied"}), 403

            request.partner = partner
            return func(*args, **kwargs)

        wrapper.__name__ = func.__name__
        return wrapper
    return decorator