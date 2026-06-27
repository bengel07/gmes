# routes/partner_routes.py
from flask import Blueprint, request, jsonify, current_app
from middleware.auth import jwt_required, admin_required
from extensions import db
from models import Partner, PartnerAPIKey, PartnerWebhook, PartnerTransaction
from services.partner_service import PartnerService
from datetime import datetime

partner_bp = Blueprint('partner', __name__)


# ============ Routes Admin ============

@partner_bp.route('/admin/partners', methods=['GET'])
@jwt_required
@admin_required
def list_partners():
    """Liste tous les partenaires"""
    partners = Partner.query.all()
    return jsonify({
        'partners': [p.to_dict() for p in partners]
    }), 200




@partner_bp.route('/admin/partners', methods=['POST'])
@jwt_required
@admin_required
def create_partner():
    from services.partner_service import PartnerService

    data = request.get_json()

    try:
        result = PartnerService.create_partner(data)
        return jsonify({
            'message': 'Partner created successfully',
            'partner': result['partner'],
            'api_keys': result['api_keys']
        }), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@partner_bp.route('/admin/partners/<int:partner_id>', methods=['GET'])
@jwt_required
@admin_required
def get_partner(partner_id):
    """Détails d'un partenaire"""
    partner = Partner.query.get(partner_id)
    if not partner:
        return jsonify({'error': 'Partner not found'}), 404

    return jsonify(partner.to_dict()), 200


# @partner_bp.route('/admin/partners/<int:partner_id>', methods=['PUT'])
# @jwt_required
# @admin_required
# def update_partner(partner_id):
#     """Modifier un partenaire"""
#     partner = Partner.query.get(partner_id)
#     if not partner:
#         return jsonify({'error': 'Partner not found'}), 404
#
#     data = request.json
#     for field in ['name', 'description', 'contact_email', 'contact_phone',
#                   'contact_name', 'monthly_limit', 'per_transaction_limit',
#                   'daily_limit', 'is_active', 'is_verified']:
#         if field in data:
#             setattr(partner, field, data[field])
#
#     db.session.commit()
#     return jsonify({'message': 'Partner updated', 'partner': partner.to_dict()}), 200


@partner_bp.route('/admin/partners/<int:partner_id>/toggle', methods=['POST'])
@jwt_required
@admin_required
def toggle_partner(partner_id):
    """Activer/Désactiver un partenaire"""
    partner = Partner.query.get(partner_id)
    if not partner:
        return jsonify({'error': 'Partner not found'}), 404

    partner.is_active = not partner.is_active
    db.session.commit()

    return jsonify({
        'message': f"Partner {'activated' if partner.is_active else 'deactivated'}",
        'is_active': partner.is_active
    }), 200


@partner_bp.route('/admin/partners/<int:partner_id>/api-keys', methods=['GET'])
@jwt_required
@admin_required
def list_api_keys(partner_id):
    """Liste des clés API d'un partenaire"""
    keys = PartnerAPIKey.query.filter_by(partner_id=partner_id).all()

    return jsonify({
        'api_keys': [k.to_dict() for k in keys]
    }), 200


@partner_bp.route('/admin/partners/<int:partner_id>/api-keys', methods=['POST'])
@jwt_required
@admin_required
def generate_api_key(partner_id):
    """Générer une nouvelle clé API"""
    partner = Partner.query.get(partner_id)
    if not partner:
        return jsonify({'error': 'Partner not found'}), 404

    permissions = request.json.get('permissions', {})
    result = PartnerService.generate_api_keys(partner_id, permissions)

    return jsonify({
        'message': 'API key generated',
        'api_keys': result
    }), 201


@partner_bp.route('/admin/partners/<int:partner_id>/api-keys/<int:key_id>/regenerate', methods=['POST'])
@jwt_required
@admin_required
def regenerate_secret(partner_id, key_id):
    """Régénérer le secret d'une clé API"""
    result = PartnerService.regenerate_secret(key_id, partner_id)

    if not result:
        return jsonify({'error': 'API key not found'}), 404

    return jsonify({
        'message': 'Secret regenerated',
        'client_secret': result['client_secret']
    }), 200


@partner_bp.route('/admin/partners/<int:partner_id>/api-keys/<int:key_id>/toggle', methods=['POST'])
@jwt_required
@admin_required
def toggle_api_key(partner_id, key_id):
    """Activer/Désactiver une clé API"""
    api_key = PartnerAPIKey.query.filter_by(id=key_id, partner_id=partner_id).first()

    if not api_key:
        return jsonify({'error': 'API key not found'}), 404

    api_key.is_active = not api_key.is_active
    db.session.commit()

    return jsonify({
        'message': f"API key {'activated' if api_key.is_active else 'deactivated'}",
        'is_active': api_key.is_active
    }), 200


@partner_bp.route('/admin/partners/<int:partner_id>/webhooks', methods=['GET'])
@jwt_required
@admin_required
def list_webhooks(partner_id):
    """Liste des webhooks d'un partenaire"""
    webhooks = PartnerWebhook.query.filter_by(partner_id=partner_id).all()

    return jsonify({
        'webhooks': [{
            'id': w.id,
            'url': w.url,
            'events': w.events,
            'is_active': w.is_active,
            'failed_attempts': w.failed_attempts,
            'last_triggered_at': w.last_triggered_at.isoformat() if w.last_triggered_at else None
        } for w in webhooks]
    }), 200


@partner_bp.route('/admin/partners/<int:partner_id>/webhooks', methods=['POST'])
@jwt_required
@admin_required
def add_webhook(partner_id):
    """Ajouter un webhook"""
    data = request.json
    url = data.get('url')
    events = data.get('events', ['payment.created', 'payment.completed'])

    if not url:
        return jsonify({'error': 'URL required'}), 400

    result = PartnerService.add_webhook(partner_id, url, events)

    return jsonify({
        'message': 'Webhook added',
        'webhook': result
    }), 201


@partner_bp.route('/admin/partners/<int:partner_id>/webhooks/<int:webhook_id>', methods=['DELETE'])
@jwt_required
@admin_required
def delete_webhook(partner_id, webhook_id):
    """Supprimer un webhook"""
    webhook = PartnerWebhook.query.filter_by(id=webhook_id, partner_id=partner_id).first()

    if not webhook:
        return jsonify({'error': 'Webhook not found'}), 404

    db.session.delete(webhook)
    db.session.commit()

    return jsonify({'message': 'Webhook deleted'}), 200


@partner_bp.route('/admin/partners/<int:partner_id>/transactions', methods=['GET'])
@jwt_required
@admin_required
def list_transactions(partner_id):
    """Voir les transactions d'un partenaire"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    transactions = PartnerTransaction.query.filter_by(partner_id=partner_id) \
        .order_by(PartnerTransaction.created_at.desc()) \
        .paginate(page=page, per_page=per_page)

    return jsonify({
        'transactions': [t.to_dict() for t in transactions.items],
        'total': transactions.total,
        'page': page,
        'per_page': per_page
    }), 200


# ============ Routes API Externe (pour partenaires) ============

@partner_bp.route('/api/v1/payment', methods=['POST'])
def create_payment():
    """API partenaire: créer un paiement"""
    auth = request.authorization

    if not auth:
        return jsonify({'error': 'API key required'}), 401

    # Vérifier les identifiants
    api_key = PartnerService.verify_api_key(auth.username, auth.password)

    if not api_key:
        return jsonify({'error': 'Invalid API credentials'}), 401

    # Vérifier permission
    if not api_key.permissions.get('can_create_payment', False):
        return jsonify({'error': 'Permission denied'}), 403

    data = request.json
    partner = Partner.query.get(api_key.partner_id)

    # Vérifier limites
    if data.get('amount', 0) > partner.per_transaction_limit:
        return jsonify({'error': f"Amount exceeds limit of {partner.per_transaction_limit}"}), 400

    try:
        transaction = PartnerService.create_payment(api_key.partner_id, data)
        return jsonify(transaction), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@partner_bp.route('/api/v1/balance', methods=['GET'])
def check_balance():
    """API partenaire: vérifier solde"""
    auth = request.authorization

    if not auth:
        return jsonify({'error': 'API key required'}), 401

    api_key = PartnerService.verify_api_key(auth.username, auth.password)

    if not api_key:
        return jsonify({'error': 'Invalid API credentials'}), 401

    if not api_key.permissions.get('can_check_balance', False):
        return jsonify({'error': 'Permission denied'}), 403

    partner = Partner.query.get(api_key.partner_id)

    return jsonify({
        'balance': float(partner.wallet_balance),
        'currency': 'HTG',
        'partner_id': partner.id,
        'partner_name': partner.name
    }), 200


@partner_bp.route('/api/v1/transaction/<reference>', methods=['GET'])
def get_transaction(reference):
    """API partenaire: voir transaction"""
    auth = request.authorization

    if not auth:
        return jsonify({'error': 'API key required'}), 401

    api_key = PartnerService.verify_api_key(auth.username, auth.password)

    if not api_key:
        return jsonify({'error': 'Invalid API credentials'}), 401

    transaction = PartnerTransaction.query.filter_by(reference=reference).first()

    if not transaction or transaction.partner_id != api_key.partner_id:
        return jsonify({'error': 'Transaction not found'}), 404

    return jsonify(transaction.to_dict()), 200


from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Partner, User
from extensions import db


@partner_bp.route('/admin/partners/<int:partner_id>', methods=['PUT'])
@jwt_required
def update_partner(partner_id):
    """Modifier un partenaire"""

    # ✅ Vérification admin
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user or not user.is_admin:
        return jsonify({"error": "Forbidden - Admin only"}), 403

    # ✅ Vérifier que le partenaire existe
    partner = Partner.query.get(partner_id)
    if not partner:
        return jsonify({"error": "Partner not found"}), 404

    # ✅ Récupérer les données
    data = request.get_json() or {}

    # ✅ Mise à jour des champs principaux
    if "name" in data:
        partner.name = data["name"]

    if "contact_email" in data:
        partner.contact_email = data["contact_email"]

    if "contact_phone" in data:
        partner.contact_phone = data["contact_phone"]

    if "per_transaction_limit" in data:
        partner.per_transaction_limit = float(data["per_transaction_limit"])

    if "is_active" in data:
        partner.is_active = bool(data["is_active"])

    # ✅ Sauvegarde
    db.session.commit()

    return jsonify({
        "message": "Partner updated successfully",
        "partner": {
            'id': partner.id,
            'name': partner.name,
            'contact_email': partner.contact_email,
            'contact_phone': partner.contact_phone,
            'per_transaction_limit': float(partner.per_transaction_limit) if partner.per_transaction_limit else None,
            'is_active': partner.is_active
        }
    }), 200