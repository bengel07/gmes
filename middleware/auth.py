from functools import wraps
from flask import request, jsonify, current_app, g
import jwt



def jwt_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):

        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return jsonify({'error': 'Missing authorization header'}), 401

        parts = auth_header.split()

        if len(parts) != 2 or parts[0] != "Bearer":
            return jsonify({'error': 'Invalid authorization header'}), 401

        token = parts[1]

        try:
            payload = jwt.decode(
                token,
                current_app.config['JWT_SECRET_KEY'],
                algorithms=['HS256']
            )

            g.user_id = payload.get('user_id')
            g.user_email = payload.get('email')

        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401

        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        return f(*args, **kwargs)

    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        from models import User
        user = User.query.get(g.user_id)
        if not user or not user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)

    return decorated

def agent_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        from models import User
        user = User.query.get(g.user_id)
        if not user or not user.is_agent:
            return jsonify({'error': 'Agent access required'}), 403
        return f(*args, **kwargs)
    return decorated