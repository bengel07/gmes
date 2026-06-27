import bcrypt
import jwt
from flask import current_app
from datetime import datetime, timedelta
import uuid



SECRET = "SUPER_SECRET_KEY"

def generate_jwt(user_id, email, role="user"):
    payload = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")

def hash_password(password):
    """Hacher un mot de passe"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(hashed, password):
    """Vérifier un mot de passe"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def generate_jwt(user_id, email):
    """Générer un token JWT"""
    payload = {
        'user_id': user_id,
        'email': email,
        'exp': datetime.utcnow() + current_app.config['JWT_ACCESS_TOKEN_EXPIRES'],
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, current_app.config['JWT_SECRET_KEY'], algorithm='HS256')

def generate_reference(prefix='TXN'):
    """Générer une référence unique"""
    return f"{prefix}_{uuid.uuid4().hex[:12].upper()}"

def validate_phone_haïti(phone):
    """Valider un numéro de téléphone haïtien"""
    import re
    pattern = r'^(509|01)[0-9]{8}$'
    return bool(re.match(pattern, phone))