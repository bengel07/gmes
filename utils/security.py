import hashlib
from models import Partner

def verify_partner(client_id, client_secret):
    partner = Partner.query.filter_by(client_id=client_id).first()

    if not partner:
        return None

    hashed = hashlib.sha256(client_secret.encode()).hexdigest()

    if partner.client_secret_hash != hashed:
        return None

    return partner