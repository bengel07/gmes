import jwt
from flask import Blueprint, request, jsonify, session, current_app,g
from extensions import db
from models import User, Wallet, AuditLog
from utils.audit import log_action
from utils.helpers import hash_password, verify_password, generate_jwt
import re
from middleware.auth import jwt_required

from datetime import datetime, timedelta

# from utils.email_service import (send_welcome_email, notify_admin_new_user, send_agent_request_email, notify_admin_agent_request)
from utils.email_service import (
    send_welcome_email,
    notify_admin_new_user,
    send_agent_request_email,
    notify_admin_agent_request
)

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json

    # Validation
    required_fields = ['email', 'password', 'first_name', 'last_name', 'phone']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400

    # Email validation
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', data['email']):
        return jsonify({'error': 'Invalid email format'}), 400

    # Phone validation - international (7-15 chiffres)
    phone_clean = re.sub(r'[\s\-\(\)\+]', '', data['phone'])
    if not re.match(r'^[0-9]{7,15}$', phone_clean):
        return jsonify({'error': 'Invalid phone number. Must be 7-15 digits.'}), 400

    if int(phone_clean) == 0:
        return jsonify({'error': 'Invalid phone number'}), 400

    # Check existing user
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400

    if User.query.filter_by(phone=data['phone']).first():
        return jsonify({'error': 'Phone number already registered'}), 400

    # Create user
    user = User(
        email=data['email'],
        first_name=data['first_name'],
        last_name=data['last_name'],
        phone=data['phone'],
        password_hash=hash_password(data['password'])
    )

    db.session.add(user)
    db.session.flush()

    # Create wallet
    wallet = Wallet(user_id=user.id)
    db.session.add(wallet)


    # Audit log
    audit = AuditLog(
        user_id=user.id,
        action='user_registered',
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )
    db.session.add(audit)

    db.session.commit()

    log_action(
        action="REGISTER",
        user_id=user.id
    )

    # Envoyer email de bienvenue
    send_welcome_email(user)
    notify_admin_new_user(user)

    return jsonify({
        'message': 'User created successfully',
        'user_id': user.id,
        'email': user.email,
        'phone': user.phone
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    from utils.helpers import verify_password

    data = request.get_json(silent=True)

    print(f"Tentative login: {data.get('email')}")

    if not data.get('email') or not data.get('password'):
        print("❌ Utilisateur non trouvé")
        return jsonify({'error': 'Email and password required'}), 400

    user = User.query.filter_by(email=data['email']).first()

    user = User.query.filter_by(email=data['email']).first()

    if not user:
        return jsonify({'error': 'User not found'}), 404

    if not verify_password(user.password_hash, data['password']):
        is_valid = verify_password(user.password_hash, data.get('password'))

        print(f"Mot de passe valide: {is_valid}")
        return jsonify({'error': 'Invalid credentials'}), 401


    if not user.is_active:
        return jsonify({'error': 'Account disabled'}), 403

    # Generate JWT
    token = generate_jwt(user.id, user.email)

    # Session Flask
    session['user_id'] = user.id
    session['email'] = user.email
    session['is_admin'] = user.is_admin
    session['full_name'] = f"{user.first_name} {user.last_name}"

    # Audit log
    audit = AuditLog(
        user_id=user.id,
        action='user_login',
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )
    db.session.add(audit)
    db.session.commit()

    return jsonify({
        'access_token': token,
        'user': {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_admin': user.is_admin
        }
    }), 200




@auth_bp.route('/me', methods=['GET'])
@jwt_required
def get_me():
    user = User.query.get(g.user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'id': user.id,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'phone': user.phone,
        'is_verified': user.is_verified,
        'is_admin': user.is_admin,
        'created_at': user.created_at.isoformat()
    }), 200


@auth_bp.route('/agent/login', methods=['POST'])
def agent_login():
    """Connexion spéciale pour les agents"""
    data = request.json
    email = data.get('email')
    password = data.get('password')
    agent_code = data.get('agent_code')  # Code unique de l'agent

    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400

    user = User.query.filter_by(email=email).first()

    if not user or not verify_password(user.password_hash, password):
        return jsonify({'error': 'Invalid credentials'}), 401

    # Vérifier que c'est bien un agent
    if not user.is_agent:
        return jsonify({'error': 'Access denied. Not an agent account.'}), 403

    # Vérifier le code agent (optionnel)
    if agent_code and user.agent_code != agent_code:
        return jsonify({'error': 'Invalid agent code'}), 403

    if not user.is_active:
        return jsonify({'error': 'Account disabled'}), 403

    # Générer JWT avec rôle agent
    token = generate_jwt(user.id, user.email, role='agent')

    return jsonify({
        'access_token': token,
        'user': {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_agent': user.is_agent,
            'is_admin': user.is_admin,
            'agent_code': user.agent_code,
            'agent_balance': float(user.agent_balance) if user.agent_balance else 0
        }
    }), 200

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.json
    email = data.get('email')

    if not email:
        return jsonify({"error": "Email required"}), 400

    user = User.query.filter_by(email=email).first()

    # sécurité: toujours même réponse
    if not user:
        return jsonify({"message": "If email exists, reset link sent"}), 200

    token = jwt.encode({
        "user_id": user.id,
        "exp": datetime.utcnow() + timedelta(minutes=15)
    }, current_app.config['JWT_SECRET_KEY'], algorithm="HS256")

    # ici normalement email (ou log en dev)
    reset_link = f"http://127.0.0.1:5000/reset-password?token={token}"

    print("RESET LINK:", reset_link)

    return jsonify({"message": "Reset link sent"}), 200


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.json
    token = data.get("token")
    new_password = data.get("password")

    if not token or not new_password:
        return jsonify({"error": "Missing data"}), 400

    try:
        payload = jwt.decode(
            token,
            current_app.config['JWT_SECRET_KEY'],
            algorithms=["HS256"]
        )

        user = User.query.get(payload["user_id"])

        if not user:
            return jsonify({"error": "User not found"}), 404

        user.password_hash = hash_password(new_password)

        db.session.commit()

        return jsonify({"message": "Password updated successfully"}), 200

    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired"}), 400

    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 400